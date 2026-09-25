#!/usr/bin/env python3
"""v0.6.1 step 4 boss gate — check self-test against samples (spec §4.4, rulings 7 and 10).

Boss-authored; the worker installs this file byte-for-byte and never edits it. The sample pack under
templates/adversarial-review/checks/samples/ is ALSO boss-authored and installed byte-for-byte.

Contract pinned here (boss rulings for this step):
  * `CheckSample` frozen dataclass: files (tuple of (name-inside-task-folder, sample-path) pairs in
    manifest order), expect ("pass" | "fail"), note = "", args = "", fail_contains = "";
    property `label` = note if set, else the first file NAME. `TaskSpec.check_samples: tuple[CheckSample, ...] = ()`.
  * Parse (ValueError naming the task): check_samples must be a list of objects whose keys are only
    files / expect / note / args / fail_contains (an unknown key is an error naming that key); files a
    non-empty object of str -> str whose names are relative, non-empty, not "." , contain no ".."
    segment or NUL, and do not collide once normalised (two names for one target, or a name that is
    a parent folder of another — panel round 1 A2); expect a string that is exactly "pass" or "fail";
    note/args/fail_contains strings; fail_contains on a pass sample is an error; samples on a task
    with no check are an error (the existing "check is required" rule).
  * `check_has_control_token(check) -> bool`: True when the §4.2 token list (shlex, punctuation_chars)
    contains a shell control token — any UNQUOTED token made only of the characters & | ; ( ) < >
    (so && || ; | & |& ( ) and every redirect form count, and a `( … )` subshell or `$( … )` counts —
    round 1 A1) or a standalone { or } — and an operator INSIDE quotes (`'&&'`, `--sep '>'`,
    `--verify-command 'a && b'`) is NOT a control token because the quotes are honoured (round 1
    Sonnet A2: tokenise so that quoted text keeps its quotes, e.g. shlex posix=False). A tokeniser
    error counts as chained. `effective_sample_command(check, args)` = check + " " + args when args
    is non-empty, else check (no other transformation).
  * `check_samples_skipped(task) -> bool`: True when "{{" occurs in the check, any sample path, any
    args or any note — then NO sample is executed and no sample finding is emitted, before any other
    sample rule (placeholder manifests lint exactly as today: X3).
  * Lint (standalone `lint` and the implicit lint at `run`, incl. --dry-run), per executed sample:
    prints one progress line to stdout BEFORE executing —
        "lint: sample <task_key>/<label>: <effective command>"
    creates a throwaway folder via tempfile.mkdtemp(prefix=SAMPLE_DIR_PREFIX) (SAMPLE_DIR_PREFIX =
    "ringer-sample-"), copies the named files in under their names (creating parent folders for a
    name such as "notes/extra.txt"; the originals are never touched), executes the effective command
    with the shell in that folder (stdin closed, new session, process group killed on timeout) under
    the task's check_timeout_s (default CHECK_TIMEOUT_S), then removes the folder whatever happened
    (a removal error is printed, never raised).
  * Outcome vs expect: exit 0 satisfies "pass"; a non-zero exit satisfies "fail" only when
    fail_contains is empty or occurs case-insensitively in the check's output; a timed-out sample
    satisfies NEITHER. Mismatch -> one ERROR finding whose FIRST line is exactly one of
        "ERROR: <key>: sample <label>: expected pass, got fail (exit <n>)"
        "ERROR: <key>: sample <label>: expected fail, got pass (exit 0)"
        "ERROR: <key>: sample <label>: expected fail containing <fail_contains!r>, got fail (exit <n>) without it"
        "ERROR: <key>: sample <label>: expected <pass|fail>, got timeout (after <n>s)"
    followed by a line containing the effective command and the last lines of the check's output.
  * Other ERROR findings (nothing executed for that sample):
        "ERROR: <key>: sample <label>: sample cannot take args on a chained check"   (args + control token)
        "ERROR: <key>: sample <label>: sample file <path> not found"
        "ERROR: <key>: sample <label>: sample file <path> could not be copied: <reason>"  (copy OSError —
        the folder is still removed; round 1 Sonnet A1)
    Precedence per sample: placeholder skip (whole task) → args-on-chained → file missing → copy.
  * `run` refuses on any ERROR before any worker is spawned (no run state, no model-log row).
  * Run-time behaviour of a task is unchanged by its samples. `run --dry-run`'s plan prints nothing
    new for samples (the progress lines are the trace).
  * Sample pack: templates/adversarial-review/checks/samples/ (the 10 boss files); the template
    manifest's reviewer tasks carry check_samples over "{{KIT_DIR}}/checks/samples/<file>" with
    fail_contains on every fail sample; templates still lint clean; the pack resolved to a real
    path lints with zero ERROR findings — which requires check_review_report.py to accept
    heading/bold/bulleted/numbered-list label decoration while still failing the three fail samples
    for their stated reasons; a Finding: block inside a ``` fenced code block is not a finding, and
    every required label needs a non-empty value (round 1 GPT A3 / Sonnet A6).
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RINGER_PATH = ROOT / "ringer.py"
KIT_DIR = ROOT / "templates" / "adversarial-review"
SAMPLES_DIR = KIT_DIR / "checks" / "samples"
TEMPLATE_CHECK = KIT_DIR / "checks" / "check_review_report.py"
sys.path.insert(0, str(ROOT))

import ringer  # noqa: E402
from ringer import (  # noqa: E402
    CHECK_TIMEOUT_S,
    SAMPLE_DIR_PREFIX,
    CheckSample,
    Manifest,
    TaskSpec,
    check_has_control_token,
    check_samples_skipped,
    effective_sample_command,
    lint_manifest,
)

LONG_SPEC = (
    "You are a worker in a gate fixture. Create out.txt containing the word done, in the current "
    "working directory. Do not create other files. This spec is deliberately long enough that "
    "lint's underspecified-spec rule does not fire on it."
)

PASS_SAMPLES = (
    "pass-heading-markers.md",
    "pass-bold-labels.md",
    "pass-bulleted-labels.md",
    "pass-wrapped-summary.md",
    "pass-label-continues.md",
    "pass-no-findings-caps.md",
    "pass-no-findings-sentence.md",
)
FAIL_SAMPLES = {
    "fail-missing-priority.md": "Priority",
    "fail-missing-summary.md": "Summary",
    "fail-reviewer-patched.md": "must not fix",
}


def task_obj(key: str, check: str, **overrides: object) -> dict[str, object]:
    obj: dict[str, object] = {
        "key": key,
        "spec": LONG_SPEC,
        "check": check,
        "expect_files": ["report.md"],
        "task_type": "probe",
        "verified": "the gate fixture check holds",
    }
    obj.update(overrides)
    return obj


def manifest_obj(tasks: list[dict[str, object]], workdir: str) -> dict[str, object]:
    return {"run_name": "gate-samples", "workdir": workdir, "max_parallel": 1, "tasks": tasks}


class TempDirMixin:
    def make_root(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-s4-")
        self.addCleanup(tmp.cleanup)  # type: ignore[attr-defined]
        return Path(tmp.name)

    def isolate_tmpdir(self, root: Path) -> Path:
        """Point the process temp dir at a fresh folder so sample-folder removal is observable."""
        sample_tmp = root / "tmp"
        sample_tmp.mkdir()
        old_env = os.environ.get("TMPDIR")
        old_cached = tempfile.tempdir

        def restore() -> None:
            if old_env is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old_env
            tempfile.tempdir = old_cached

        self.addCleanup(restore)  # type: ignore[attr-defined]
        os.environ["TMPDIR"] = str(sample_tmp)
        tempfile.tempdir = None
        return sample_tmp

    def write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text, encoding="utf-8")
        return path


class ParseTests(unittest.TestCase):
    def test_check_samples_parse_in_order_with_defaults(self) -> None:
        task = TaskSpec.from_obj(task_obj("t", "grep ok report.md", check_samples=[
            {"files": {"report.md": "/tmp/a.md"}, "expect": "pass"},
            {"files": {"report.md": "/tmp/b.md", "extra.txt": "/tmp/e.txt"}, "expect": "fail",
             "note": "missing label", "args": "--head abc1234", "fail_contains": "Priority"},
        ]))
        self.assertEqual(2, len(task.check_samples))
        first, second = task.check_samples
        self.assertIsInstance(first, CheckSample)
        self.assertTrue(dataclasses.is_dataclass(first))
        self.assertEqual((("report.md", "/tmp/a.md"),), first.files)
        self.assertEqual("pass", first.expect)
        self.assertEqual(("", "", ""), (first.note, first.args, first.fail_contains))
        self.assertEqual("report.md", first.label)
        self.assertEqual((("report.md", "/tmp/b.md"), ("extra.txt", "/tmp/e.txt")), second.files)
        self.assertEqual(("fail", "missing label", "--head abc1234", "Priority"),
                         (second.expect, second.note, second.args, second.fail_contains))
        self.assertEqual("missing label", second.label)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.expect = "fail"  # type: ignore[misc]

    def test_no_samples_is_an_empty_tuple(self) -> None:
        self.assertEqual((), TaskSpec.from_obj(task_obj("t", "grep ok report.md")).check_samples)

    def test_parse_errors_name_the_task(self) -> None:
        bad = [
            ({"check_samples": {"files": {}}}, "check_samples"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "maybe"}]}, "expect"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}}]}, "expect"),
            ({"check_samples": [{"files": {}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": "/tmp/a.md", "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"/abs/report.md": "/tmp/a.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"../report.md": "/tmp/a.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"report.md": 7}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "pass", "args": 3}]}, "args"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "pass", "note": []}]}, "note"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "fail", "fail_contains": 1}]}, "fail_contains"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "pass", "fail_contains": "x"}]}, "fail_contains"),
            # round 1 folds: A2 (both seats) name holes; Sonnet A1 unhashable expect; Sonnet A3 unknown keys
            ({"check_samples": [{"files": {"": "/tmp/a.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {".": "/tmp/a.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"a": "/tmp/a.md", "a/b": "/tmp/b.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md", "./report.md": "/tmp/b.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"re\x00port.md": "/tmp/a.md"}, "expect": "pass"}]}, "files"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": ["pass"]}]}, "expect"),
            ({"check_samples": [{"files": {"report.md": "/tmp/a.md"}, "expect": "fail", "failcontains": "x"}]}, "failcontains"),
        ]
        for overrides, word in bad:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError) as ctx:
                    TaskSpec.from_obj(task_obj("badtask", "grep ok report.md", **overrides))
                self.assertIn("badtask", str(ctx.exception))
                self.assertIn(word, str(ctx.exception))

    def test_samples_without_a_check_are_refused(self) -> None:
        obj = task_obj("nocheck", "", check_samples=[{"files": {"report.md": "/tmp/a.md"}, "expect": "pass"}])
        with self.assertRaises(ValueError) as ctx:
            TaskSpec.from_obj(obj)
        self.assertIn("check", str(ctx.exception))


class HelperTests(unittest.TestCase):
    def test_control_tokens(self) -> None:
        chained = [
            "a && b", "a || b", "a; b", "a | b", "a & b", "a > out.txt", "a >> out.txt", "a 2>&1",
            "a < in.txt", "a || { echo no; exit 1; }", "test -f x && grep ok x",
            # round 1 A1 (GPT P1 / Sonnet A2): grouping and the pipe-both operator
            "( python3 /abs/check.py )", "(python3 /abs/check.py)", "a |& b", "$(python3 /abs/check.py)",
        ]
        for check in chained:
            with self.subTest(check=check):
                self.assertTrue(check_has_control_token(check))
        plain = [
            "python3 /abs/check.py --file report.md",
            "python3 /abs/check.py --verify-command 'pytest -q && echo ok'",
            'python3 /abs/check.py --pattern "a|b"',
            "python3 /abs/check.py --note 'x > y'",
            # round 1 Sonnet A2: a quoted BARE operator is still quoted text
            "python3 /abs/check.py '&&'", "grep -c '|' report.md", "python3 /abs/check.py --sep '>'",
            'python3 /abs/check.py ";"', "find . -name x.md -exec cat '{}' ';'",
        ]
        for check in plain:
            with self.subTest(check=check):
                self.assertFalse(check_has_control_token(check))

    def test_effective_command(self) -> None:
        self.assertEqual("python3 /abs/c.py --file report.md --head abc1234",
                         effective_sample_command("python3 /abs/c.py --file report.md", "--head abc1234"))
        self.assertEqual("python3 /abs/c.py --file report.md",
                         effective_sample_command("python3 /abs/c.py --file report.md", ""))

    def test_placeholder_skip(self) -> None:
        def task(check: str = "python3 /abs/c.py --file report.md", **sample: object) -> TaskSpec:
            base: dict[str, object] = {"files": {"report.md": "/abs/s.md"}, "expect": "pass"}
            base.update(sample)
            return TaskSpec.from_obj(task_obj("t", check, check_samples=[base]))

        self.assertFalse(check_samples_skipped(task()))
        self.assertTrue(check_samples_skipped(task(check="python3 '{{KIT_DIR}}/c.py' --file report.md")))
        self.assertTrue(check_samples_skipped(task(files={"report.md": "{{KIT_DIR}}/samples/s.md"})))
        self.assertTrue(check_samples_skipped(task(args="--head {{COMMIT}}")))
        self.assertTrue(check_samples_skipped(task(note="{{NOTE}}")))
        self.assertFalse(check_samples_skipped(TaskSpec.from_obj(task_obj("t", "python3 '{{KIT_DIR}}/c.py'"))),
                         "a task with no samples has nothing to skip")


class LintSampleTests(TempDirMixin, unittest.TestCase):
    """Sample execution through lint_manifest, in-process."""

    def setUp(self) -> None:
        self.root = self.make_root()
        self.sample_tmp = self.isolate_tmpdir(self.root)
        self.good = self.write(self.root, "good.md", "## Summary\nfine\n## Findings\nNO FINDINGS\n")
        self.bad = self.write(self.root, "bad.md", "## Summary\nfine\n## Findings\nnothing here\n")
        # A check that reads only its working directory: PASS when report.md carries NO FINDINGS.
        self.check = self.write(self.root, "check.py", (
            "import re, sys, pathlib\n"
            "text = pathlib.Path('report.md').read_text()\n"
            "print('checking', pathlib.Path.cwd())\n"
            "if re.search(r'NO FINDINGS', text):\n"
            "    print('PASS: explicit no-findings'); sys.exit(0)\n"
            "print('FAIL:'); print(' - report must contain NO FINDINGS or a Finding: block'); sys.exit(1)\n"
        ))
        # A check that also insists on --head <commit> in the report (E2's shape).
        self.head_check = self.write(self.root, "head_check.py", (
            "import argparse, pathlib, sys\n"
            "p = argparse.ArgumentParser(); p.add_argument('--file', default='report.md'); p.add_argument('--head', default='')\n"
            "a = p.parse_known_args()[0]; text = pathlib.Path(a.file).read_text()\n"
            "if a.head and a.head not in text:\n"
            "    print(f'FAIL: report never names the reviewed HEAD {a.head!r}'); sys.exit(1)\n"
            "print('PASS'); sys.exit(0)\n"
        ))
        self.report_with_head = self.write(self.root, "headed.md", "Reviewed HEAD: eb8eccd\n## Summary\nok\n")

    def lint(self, tasks: list[dict[str, object]]) -> tuple[list[str], str]:
        manifest = Manifest.from_obj(manifest_obj(tasks, str(self.root / "work")))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            findings = lint_manifest(manifest)
        return findings, buf.getvalue()

    def errors(self, findings: list[str]) -> list[str]:
        return [f for f in findings if f.startswith("ERROR:")]

    def assert_no_sample_folders_left(self) -> None:
        left = [p.name for p in self.sample_tmp.iterdir() if p.name.startswith(SAMPLE_DIR_PREFIX)]
        self.assertEqual([], left, "sample folders must be removed whatever happened")

    def test_pass_and_fail_samples_that_agree_are_clean_and_print_progress(self) -> None:
        check = f"python3 {self.check}"
        findings, out = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass", "note": "clean report"},
            {"files": {"report.md": str(self.bad)}, "expect": "fail"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assertIn(f"lint: sample t/clean report: {check}\n", out)
        self.assertIn(f"lint: sample t/report.md: {check}\n", out)
        self.assert_no_sample_folders_left()

    def test_pass_sample_that_fails_is_an_error_with_command_and_output(self) -> None:
        check = f"python3 {self.check}"
        findings, out = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.bad)}, "expect": "pass", "note": "good work"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(1, len(errs), findings)
        lines = errs[0].splitlines()
        self.assertEqual("ERROR: t: sample good work: expected pass, got fail (exit 1)", lines[0])
        self.assertIn(check, errs[0])
        self.assertIn("report must contain NO FINDINGS or a Finding: block", errs[0], "last output lines are in the finding")
        self.assertIn(f"lint: sample t/good work: {check}\n", out, "the effective command is printed before running")
        self.assert_no_sample_folders_left()

    def test_fail_sample_that_passes_is_an_error(self) -> None:
        findings, _ = self.lint([task_obj("t", f"python3 {self.check}", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "fail"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(1, len(errs), findings)
        self.assertEqual("ERROR: t: sample report.md: expected fail, got pass (exit 0)", errs[0].splitlines()[0])

    def test_fail_contains_is_case_insensitive_and_its_miss_is_an_error(self) -> None:
        check = f"python3 {self.check}"
        findings, _ = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.bad)}, "expect": "fail", "fail_contains": "no findings or a finding: BLOCK"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        findings, _ = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.bad)}, "expect": "fail", "fail_contains": "Priority"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(1, len(errs), findings)
        self.assertEqual("ERROR: t: sample report.md: expected fail containing 'Priority', got fail (exit 1) without it",
                         errs[0].splitlines()[0])

    def test_a_crashing_check_does_not_satisfy_a_fail_sample_with_fail_contains(self) -> None:
        # exit 127 (command not found) is a non-zero exit — fail_contains is what keeps it honest.
        findings, _ = self.lint([task_obj("t", "sh -c 'echo nosuch: command not found; exit 127'", check_samples=[
            {"files": {"report.md": str(self.bad)}, "expect": "fail", "fail_contains": "missing Summary"},
        ])])
        errs = self.errors(findings)
        self.assertTrue(errs and "without it" in errs[0].splitlines()[0], findings)

    def test_args_are_appended_to_the_effective_command(self) -> None:
        check = f"python3 {self.head_check} --file report.md"
        findings, out = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.report_with_head)}, "expect": "pass", "args": "--head eb8eccd"},
            {"files": {"report.md": str(self.report_with_head)}, "expect": "fail", "args": "--head 0000000",
             "fail_contains": "never names the reviewed HEAD", "note": "wrong head"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assertIn(f"lint: sample t/report.md: {check} --head eb8eccd\n", out)
        self.assertIn(f"lint: sample t/wrong head: {check} --head 0000000\n", out)

    def test_args_on_a_chained_check_is_an_error_and_nothing_runs(self) -> None:
        marker = self.root / "ran.marker"
        check = f"python3 {self.check} && touch {marker}"
        findings, out = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass", "args": "--head x", "note": "chained"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(["ERROR: t: sample chained: sample cannot take args on a chained check"], errs, findings)
        self.assertFalse(marker.exists(), "a sample refused for args must not execute")
        self.assertNotIn("lint: sample t/chained", out)

    def test_chained_check_without_args_runs_and_quoted_operator_with_args_runs(self) -> None:
        marker = self.root / "ran.marker"
        findings, _ = self.lint([task_obj("t", f"python3 {self.check} && touch {marker}", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assertTrue(marker.exists(), "a chained check with a sample that carries no args executes")
        findings, _ = self.lint([task_obj("t", f"python3 {self.head_check} --file report.md", check_samples=[
            {"files": {"report.md": str(self.report_with_head)}, "expect": "pass", "args": "--head eb8eccd"},
        ])])
        self.assertEqual([], self.errors(findings))
        quoted = f"python3 {self.head_check} --file report.md --head 'x && y'"
        findings, _ = self.lint([task_obj("t", quoted, check_samples=[
            {"files": {"report.md": str(self.report_with_head)}, "expect": "pass", "args": "--head eb8eccd"},
        ])])
        self.assertEqual([], self.errors(findings), "an operator inside a quoted argument is not a control token; argparse: last --head wins")

    def test_missing_sample_file_is_an_error_and_not_executed(self) -> None:
        missing = self.root / "nope.md"
        findings, out = self.lint([task_obj("t", f"python3 {self.check}", check_samples=[
            {"files": {"report.md": str(missing)}, "expect": "pass", "note": "gone"},
        ])])
        self.assertEqual([f"ERROR: t: sample gone: sample file {missing} not found"], self.errors(findings), findings)
        self.assertNotIn("lint: sample t/gone", out)
        self.assert_no_sample_folders_left()

    def test_placeholders_skip_samples_entirely(self) -> None:
        marker = self.root / "ran.marker"
        check = f"python3 {self.check} && touch {marker}"
        for sample in (
            {"files": {"report.md": "{{KIT_DIR}}/samples/s.md"}, "expect": "pass"},
            {"files": {"report.md": str(self.root / "missing.md")}, "expect": "pass", "args": "--head {{COMMIT}}"},
            {"files": {"report.md": str(self.root / "missing.md")}, "expect": "pass", "note": "{{NOTE}}"},
        ):
            with self.subTest(sample=sample):
                findings, out = self.lint([task_obj("t", check, check_samples=[sample])])
                self.assertEqual([], [f for f in findings if "sample" in f], findings)
                self.assertNotIn("lint: sample", out)
                self.assertFalse(marker.exists())
        findings, out = self.lint([task_obj("t", "python3 '{{KIT_DIR}}/checks/c.py' --file report.md", check_samples=[
            {"files": {"report.md": str(self.root / "missing.md")}, "expect": "pass", "args": "--head x"},
        ])])
        self.assertEqual([], [f for f in findings if f.startswith("ERROR:")], "a placeholder check skips samples before the chained/args and file rules")
        self.assertNotIn("lint: sample", out)

    def test_sample_runs_in_its_own_folder_with_the_named_files_and_is_bounded_by_check_timeout_s(self) -> None:
        # The check records its cwd and lists it; the sample folder must be under the temp dir, hold
        # exactly the named files, and be gone afterwards.
        recorder = self.root / "cwd.txt"
        check = f"python3 -c \"import os,pathlib; pathlib.Path('{recorder}').write_text(os.getcwd()+chr(10)+' '.join(sorted(os.listdir())))\""
        findings, _ = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.good), "notes/extra.txt": str(self.bad)}, "expect": "pass"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        cwd, listing = recorder.read_text().splitlines()
        self.assertTrue(Path(cwd).name.startswith(SAMPLE_DIR_PREFIX), cwd)
        self.assertEqual(str(self.sample_tmp.resolve()), str(Path(cwd).resolve().parent))
        self.assertEqual("notes report.md", listing)
        self.assert_no_sample_folders_left()
        # Timeout: a hanging sample never satisfies either expectation, and its folder is still removed.
        for expect in ("pass", "fail"):
            with self.subTest(expect=expect):
                findings, _ = self.lint([task_obj("t", "sleep 20", check_timeout_s=1, check_samples=[
                    {"files": {"report.md": str(self.good)}, "expect": expect, "note": "hang"},
                ])])
                errs = self.errors(findings)
                self.assertEqual(1, len(errs), findings)
                self.assertEqual(f"ERROR: t: sample hang: expected {expect}, got timeout (after 1s)", errs[0].splitlines()[0])
                self.assert_no_sample_folders_left()

    # ---- round-1 panel folds and gate blind spots (Sonnet A4/A5) ----
    def test_placeholder_in_one_samples_note_skips_every_sample_of_the_task(self) -> None:
        marker = self.root / "ran.marker"
        findings, out = self.lint([task_obj("t", f"python3 {self.check} && touch {marker}", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass", "note": "plain"},
            {"files": {"report.md": str(self.good)}, "expect": "pass", "note": "{{LATER}}"},
        ])])
        self.assertEqual([], [f for f in findings if "sample" in f], findings)
        self.assertNotIn("lint: sample", out)
        self.assertFalse(marker.exists(), "a placeholder anywhere in the task's samples skips ALL of them")

    def test_precedence_args_on_chained_beats_missing_file(self) -> None:
        missing = self.root / "nope.md"
        findings, _ = self.lint([task_obj("t", f"python3 {self.check} && true", check_samples=[
            {"files": {"report.md": str(missing)}, "expect": "pass", "args": "--head x", "note": "both"},
        ])])
        self.assertEqual(["ERROR: t: sample both: sample cannot take args on a chained check"], self.errors(findings), findings)

    def test_subshell_check_refuses_args_but_runs_without_them(self) -> None:
        findings, _ = self.lint([task_obj("t", f"( python3 {self.check} )", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass", "args": "--head x", "note": "grouped"},
        ])])
        self.assertEqual(["ERROR: t: sample grouped: sample cannot take args on a chained check"], self.errors(findings), findings)
        findings, _ = self.lint([task_obj("t", f"( python3 {self.check} )", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass"},
        ])])
        self.assertEqual([], self.errors(findings), findings)

    def test_quoted_operator_check_takes_args(self) -> None:
        check = f"python3 {self.head_check} --file report.md --note '&&'"
        findings, out = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.report_with_head)}, "expect": "pass", "args": "--head eb8eccd"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assertIn(f"lint: sample t/report.md: {check} --head eb8eccd\n", out)

    def test_exit_127_without_fail_contains_satisfies_a_fail_sample(self) -> None:
        findings, _ = self.lint([task_obj("t", "sh -c 'echo nosuch: command not found; exit 127'", check_samples=[
            {"files": {"report.md": str(self.bad)}, "expect": "fail"},
        ])])
        self.assertEqual([], self.errors(findings), "without fail_contains, fail means any non-zero exit (pinned)")

    def test_unreadable_sample_file_is_a_copy_error_and_the_folder_is_removed(self) -> None:
        locked = self.write(self.root, "locked.md", "## Summary\nx\n")
        locked.chmod(0o000)
        self.addCleanup(lambda: locked.chmod(0o644))
        findings, out = self.lint([task_obj("t", f"python3 {self.check}", check_samples=[
            {"files": {"report.md": str(locked)}, "expect": "pass", "note": "locked"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(1, len(errs), findings)
        self.assertTrue(errs[0].startswith(f"ERROR: t: sample locked: sample file {locked} could not be copied: "), errs[0])
        self.assert_no_sample_folders_left()

    def test_timeout_finding_carries_the_progress_line_first_and_the_timed_out_excerpt(self) -> None:
        check = "sh -c 'echo starting; sleep 20'"
        findings, out = self.lint([task_obj("t", check, check_timeout_s=1, check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass", "note": "hang"},
        ])])
        errs = self.errors(findings)
        self.assertEqual(1, len(errs), findings)
        self.assertIn(f"lint: sample t/hang: {check}\n", out, "the progress line is printed before execution, even for a sample that never returns")
        self.assertIn("starting", errs[0], "output produced before the timeout is in the excerpt")
        self.assertIn("[ringer.py] check timed out after 1s", errs[0])
        self.assert_no_sample_folders_left()

    def test_sample_folder_is_removed_when_the_check_leaves_files_behind(self) -> None:
        check = "sh -c 'mkdir -p deep/er && echo x > deep/er/file && exit 0'"
        findings, _ = self.lint([task_obj("t", check, check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assert_no_sample_folders_left()

    def test_sample_files_are_copies_the_originals_are_untouched(self) -> None:
        before = self.good.read_bytes()
        findings, _ = self.lint([task_obj("t", "sh -c 'echo clobbered > report.md; rm -f report.md; exit 0'", check_samples=[
            {"files": {"report.md": str(self.good)}, "expect": "pass"},
        ])])
        self.assertEqual([], self.errors(findings), findings)
        self.assertEqual(before, self.good.read_bytes())


class CliTests(TempDirMixin, unittest.TestCase):
    """Standalone lint, run --dry-run and run through the real CLI with a /bin/sh fake engine."""

    def setUp(self) -> None:
        self.root = self.make_root()
        self.sample_tmp = self.isolate_tmpdir(self.root)
        self.old_env = os.environ.copy()
        self.addCleanup(self._restore_env)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["RINGER_HOME"] = str(self.root / "ringer-home")
        self.config_path = self.root / "config.toml"
        self.jsonl_path = self.root / "runs.jsonl"
        self.state_dir = self.root / "state"
        self.marker = self.root / "worker-ran.marker"
        self.good = self.write(self.root, "good.md", "## Summary\nfine\n## Findings\nNO FINDINGS\n")
        self.bad = self.write(self.root, "bad.md", "## Summary\nfine\n## Findings\nnothing here\n")
        self.check = self.write(self.root, "check.sh", "#!/bin/sh\ngrep -q 'NO FINDINGS' report.md && { echo PASS; exit 0; }\necho 'FAIL: no NO FINDINGS'; exit 1\n")
        self.config_path.write_text("\n".join([
            f'state_dir = "{self.state_dir}"',
            "dashboard_port_base = 18827",
            "allow_full_access = false",
            "",
            "[eval]",
            'backend = "jsonl"',
            f'jsonl_path = "{self.jsonl_path}"',
            "",
            "[engines.write_good]",
            'bin = "/bin/sh"',
            f'args_template = ["-c", "touch {self.marker}; printf \'## Summary\\\\nfine\\\\n## Findings\\\\nNO FINDINGS\\\\n\' > report.md"]',
            "sandbox_args = []",
            "full_access_args = []",
            'token_regex = "tokens\\\\s+used\\\\s*:?\\\\s*([0-9][0-9,]*)"',
            "",
        ]), encoding="utf-8")

    def _restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def manifest(self, name: str, samples: list[dict[str, object]]) -> Path:
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(manifest_obj([
            task_obj("lane", f"sh {self.check}", engine="write_good", check_samples=samples, max_attempts=1),
        ], str(self.root / f"work-{name}"))), encoding="utf-8")
        return path

    def cli(self, *argv: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(RINGER_PATH), "--config", str(self.config_path), *argv],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False,
        )

    def no_sample_folders_left(self) -> None:
        self.assertEqual([], [p.name for p in self.sample_tmp.iterdir() if p.name.startswith(SAMPLE_DIR_PREFIX)])

    def test_standalone_lint_exit_codes_and_progress(self) -> None:
        ok = self.manifest("ok", [{"files": {"report.md": str(self.good)}, "expect": "pass"},
                                  {"files": {"report.md": str(self.bad)}, "expect": "fail", "fail_contains": "no NO FINDINGS"}])
        proc = self.cli("lint", str(ok))
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertEqual(2, proc.stdout.count("lint: sample lane/report.md: "), proc.stdout)
        self.assertIn("lint: clean (1 tasks)", proc.stdout)
        bad = self.manifest("bad", [{"files": {"report.md": str(self.bad)}, "expect": "pass", "note": "E2"}])
        proc = self.cli("lint", str(bad))
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("lint: ERROR: lane: sample E2: expected pass, got fail (exit 1)", proc.stdout)
        self.assertIn(f"sh {self.check}", proc.stdout)
        self.assertIn("FAIL: no NO FINDINGS", proc.stdout, "the check's last output lines are shown")
        self.no_sample_folders_left()

    def test_dry_run_executes_samples_and_refuses_on_mismatch_before_any_worker(self) -> None:
        bad = self.manifest("dry-bad", [{"files": {"report.md": str(self.bad)}, "expect": "pass"}])
        proc = self.cli("run", str(bad), "--dry-run", "--no-dashboard", "--identity", "gate")
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("lint: ERROR: lane: sample report.md: expected pass, got fail (exit 1)", proc.stdout)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.jsonl_path.exists())
        self.assertEqual([], list((self.state_dir / "runs").glob("*.json")) if (self.state_dir / "runs").exists() else [])
        ok = self.manifest("dry-ok", [{"files": {"report.md": str(self.good)}, "expect": "pass"}])
        proc = self.cli("run", str(ok), "--dry-run", "--no-dashboard", "--identity", "gate")
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertIn("lint: sample lane/report.md: ", proc.stdout)
        self.assertNotIn("check_samples", proc.stdout, "the dry-run plan prints nothing new for samples")
        self.assertFalse(self.marker.exists(), "dry-run spawns no worker")
        self.no_sample_folders_left()

    def test_run_refuses_on_sample_mismatch_and_passes_normally_when_samples_agree(self) -> None:
        bad = self.manifest("run-bad", [{"files": {"report.md": str(self.bad)}, "expect": "pass"}])
        proc = self.cli("run", str(bad), "--no-dashboard", "--identity", "gate")
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertFalse(self.marker.exists(), "refused before any worker launched")
        self.assertFalse(self.jsonl_path.exists(), "no model-log row for a refused run")
        self.assertFalse((self.state_dir / "runs").exists() and any((self.state_dir / "runs").glob("*.json")), "no run state for a refused run")
        ok = self.manifest("run-ok", [{"files": {"report.md": str(self.good)}, "expect": "pass"},
                                      {"files": {"report.md": str(self.bad)}, "expect": "fail"}])
        proc = self.cli("run", str(ok), "--no-dashboard", "--identity", "gate")
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertTrue(self.marker.exists())
        rows = [json.loads(l) for l in self.jsonl_path.read_text().splitlines() if l.strip()]
        self.assertEqual(1, len(rows), rows)
        self.assertEqual(("PASS", "worker-output", "executed-check"),
                         (str(rows[0]["verdict"]).upper(), rows[0].get("cause"), rows[0].get("verify_method")))
        self.no_sample_folders_left()


class SamplePackTests(TempDirMixin, unittest.TestCase):
    """The fork's synthetic sample pack, the lenient template check, and X3."""

    def test_pack_files_are_installed(self) -> None:
        self.assertTrue(SAMPLES_DIR.is_dir(), SAMPLES_DIR)
        present = sorted(p.name for p in SAMPLES_DIR.iterdir() if p.suffix == ".md")
        self.assertEqual(sorted(PASS_SAMPLES + tuple(FAIL_SAMPLES)), present)

    def run_template_check(self, sample: str) -> subprocess.CompletedProcess[str]:
        root = self.make_root()
        (root / "report.md").write_bytes((SAMPLES_DIR / sample).read_bytes())
        return subprocess.run([sys.executable, str(TEMPLATE_CHECK), "--file", "report.md"], cwd=root, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)

    def test_every_pass_sample_passes_the_template_check(self) -> None:
        for name in PASS_SAMPLES:
            with self.subTest(sample=name):
                proc = self.run_template_check(name)
                self.assertEqual(0, proc.returncode, f"{name}: {proc.stdout}")

    def test_every_fail_sample_fails_for_its_stated_reason(self) -> None:
        for name, needle in FAIL_SAMPLES.items():
            with self.subTest(sample=name):
                proc = self.run_template_check(name)
                self.assertNotEqual(0, proc.returncode, f"{name}: {proc.stdout}")
                self.assertIn(needle.lower(), proc.stdout.lower(), f"{name}: {proc.stdout}")

    def test_decorated_blocks_are_still_checked_label_by_label(self) -> None:
        # Leniency must not become blindness: a bold-decorated block with Priority: P9 still fails.
        root = self.make_root()
        text = (SAMPLES_DIR / "pass-bold-labels.md").read_text(encoding="utf-8").replace("**Priority:** P1", "**Priority:** P9")
        (root / "report.md").write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(TEMPLATE_CHECK), "--file", "report.md"], cwd=root, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("priority", proc.stdout.lower())

    def check_text(self, text: str) -> subprocess.CompletedProcess[str]:
        root = self.make_root()
        (root / "report.md").write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(TEMPLATE_CHECK), "--file", "report.md"], cwd=root, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)

    # ---- round-1 folds: GPT A3 / Sonnet A6 — leniency must not become blindness ----
    def test_a_finding_block_inside_a_fenced_code_block_is_not_a_finding(self) -> None:
        proc = self.check_text(
            "## Summary\n\nI checked the cache diff and the tests.\n\n## Findings\n\n```markdown\nFinding: example only\n"
            "Evidence: this is what a finding block looks like in this template\nImpact: none\nFix: none\n"
            "Priority: P1\nConfidence: high\n```\n"
        )
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("no findings or at least one finding", proc.stdout.lower())

    def test_an_empty_label_value_fails_naming_the_label(self) -> None:
        text = (SAMPLES_DIR / "pass-bold-labels.md").read_text(encoding="utf-8").replace(
            "**Impact:** a burst of evictions on a hot key can drop its last write", "**Impact:**")
        proc = self.check_text(text)
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("impact", proc.stdout.lower())

    def test_numbered_list_decoration_passes(self) -> None:
        proc = self.check_text(
            "## Summary\n\nReviewed the widget-cache diff; one ordering defect in the eviction path, listed below.\n\n"
            "## Findings\n\n1. **Finding:** eviction runs before the write-back completes\n"
            "2. **Evidence:** cache.py:88 — `del self._entries[key]` executes before `flush()` returns\n"
            "3. **Impact:** a burst of evictions on a hot key can drop its last write\n"
            "4. **Fix:** call flush() first, then delete the entry\n5. **Priority:** P1\n6. **Confidence:** high\n"
        )
        self.assertEqual(0, proc.returncode, proc.stdout)

    def template_manifest_obj(self) -> dict[str, object]:
        return json.loads((KIT_DIR / "manifest.json").read_text(encoding="utf-8"))

    def test_template_manifest_carries_the_pack_via_kit_dir(self) -> None:
        tasks = self.template_manifest_obj()["tasks"]
        assert isinstance(tasks, list)
        carrying = [t for t in tasks if t.get("check_samples")]
        self.assertTrue(carrying, "at least one reviewer task carries check_samples")
        for task in carrying:
            paths = {Path(str(v)).name for s in task["check_samples"] for v in s["files"].values()}
            self.assertEqual(set(PASS_SAMPLES) | set(FAIL_SAMPLES), paths, task["key"])
            for sample in task["check_samples"]:
                for value in sample["files"].values():
                    self.assertTrue(str(value).startswith("{{KIT_DIR}}/checks/samples/"), value)
                name = Path(str(next(iter(sample["files"].values())))).name
                self.assertEqual("pass" if name in PASS_SAMPLES else "fail", sample["expect"], name)
                if name in FAIL_SAMPLES:
                    self.assertEqual(FAIL_SAMPLES[name].lower(), str(sample.get("fail_contains", "")).lower(), name)

    def test_x3_templates_lint_clean_and_execute_no_sample(self) -> None:
        for path in sorted((ROOT / "templates").glob("*/manifest*.json")):
            with self.subTest(template=path.name):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    findings = lint_manifest(Manifest.from_path(path))
                self.assertEqual([], findings)
                self.assertNotIn("lint: sample", buf.getvalue())

    def test_pack_resolved_to_a_real_path_lints_with_zero_errors(self) -> None:
        root = self.make_root()
        self.isolate_tmpdir(root)
        text = json.dumps(self.template_manifest_obj()).replace("{{KIT_DIR}}", str(KIT_DIR)).replace("{{WORKDIR}}", str(root / "work"))
        manifest = Manifest.from_obj(json.loads(text))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            findings = lint_manifest(manifest)
        self.assertEqual([], [f for f in findings if f.startswith("ERROR:")], findings)
        executed = buf.getvalue().count("lint: sample ")
        self.assertGreaterEqual(executed, len(PASS_SAMPLES) + len(FAIL_SAMPLES), buf.getvalue())
        self.assertEqual([], [p.name for p in (root / "tmp").iterdir() if p.name.startswith(SAMPLE_DIR_PREFIX)])


if __name__ == "__main__":
    unittest.main()
