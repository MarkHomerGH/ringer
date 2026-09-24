#!/usr/bin/env python3
"""v0.6.1 step 2 boss gate — check-script existence fence at lint (spec §4.2, ruling 9).

Boss-authored; the worker installs this file byte-for-byte and never edits it.

Contract pinned here (boss rulings for this step):
  * `analyze_check_fence(check: str) -> CheckFenceAnalysis` — a frozen dataclass with
      fenced: tuple[str, ...]      absolute candidates (after expanduser), no '{{' — the fence set
      relative: tuple[str, ...]    relative candidates with no earlier `cd /abs` in the chain
      tokenizer_failed: bool       shlex raised; nothing fenced
    One candidate per simple command, per the §4.2 algorithm (redirects and their operand
    removed first; then split on && || ; | &; VAR=word skipped; env + its options skipped;
    interpreter word by basename sh/bash/zsh/node/python*; -c / -m => no candidate;
    --flag=value never a candidate; a bare first word only if absolute).
  * lint_manifest emits exactly:
      "ERROR: <key>: check script <path> not found"   when a fenced path is not an existing
                                                       regular file (symlink to one counts)
      "advisory: <key>: ..." naming the relative path   for each relative candidate
      "advisory: <key>: ..."                            when the tokenizer failed
  * `ringer.py lint` exits 1 on the ERROR; `ringer.py run` refuses before any worker launches
    (the existing ERROR-only abort), leaving no run state, no eval row, no task folder.
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RINGER_PATH = ROOT / "ringer.py"
sys.path.insert(0, str(ROOT))

import ringer  # noqa: E402
from ringer import Manifest, analyze_check_fence, lint_manifest  # noqa: E402

LONG_SPEC = (
    "You are a worker in a gate fixture. Create out.txt containing the word done, in the current "
    "working directory, and nothing else. Do not create other files. Do not modify anything outside "
    "the current directory. This spec is deliberately long enough that lint's underspecified-spec "
    "rule does not fire on it."
)


def task_obj(check: str, **overrides: object) -> dict[str, object]:
    obj: dict[str, object] = {
        "key": "alpha",
        "spec": LONG_SPEC,
        "check": check,
        "expect_files": ["out.txt"],
        "task_type": "probe",
        "verified": "out.txt exists and says done",
    }
    obj.update(overrides)
    return obj


def manifest_for(*tasks: dict[str, object], workdir: str = "/tmp/gate-fence") -> Manifest:
    return Manifest.from_obj({"run_name": "gate-fence", "workdir": workdir, "tasks": list(tasks)})


def errors(findings: list[str]) -> list[str]:
    return [f for f in findings if f.startswith("ERROR:")]


def advisories(findings: list[str]) -> list[str]:
    return [f for f in findings if f.startswith("advisory:")]


class CandidateAlgorithmTests(unittest.TestCase):
    """Every shape in §4.2's tested-shapes list, one assertion each."""

    def fence(self, check: str) -> tuple[list[str], list[str], bool]:
        a = analyze_check_fence(check)
        self.assertTrue(dataclasses.is_dataclass(a))
        return list(a.fenced), list(a.relative), bool(a.tokenizer_failed)

    def test_house_review_check_is_fenced(self) -> None:
        fenced, rel, _ = self.fence("python3 /abs/_check_review.py --file report.md --head cdd154a")
        self.assertEqual(["/abs/_check_review.py"], fenced)
        self.assertEqual([], rel)

    def test_gus_build_shape_cd_relative_redirect_cp(self) -> None:
        check = (
            "cd /abs/repo && skills/ea/.venv/bin/python reviews/_check_gus_fix.py --file report.md "
            "> /private/tmp/x/fix.patch && cp /private/tmp/x/fix.patch /abs/out/dir/"
        )
        fenced, rel, failed = self.fence(check)
        self.assertEqual([], fenced)
        self.assertEqual([], rel, "a relative script after cd /abs is unfenced but not advisory")
        self.assertFalse(failed)

    def test_bash_gate_is_fenced(self) -> None:
        self.assertEqual((["/abs/gates/check_x.sh"], [], False), self.fence("bash /abs/gates/check_x.sh"))

    def test_r30_shape_sh_missing(self) -> None:
        self.assertEqual((["/abs/missing.sh"], [], False), self.fence("sh /abs/missing.sh"))

    def test_quoted_path_counts(self) -> None:
        self.assertEqual((["/abs/missing.py"], [], False), self.fence("python3 '/abs/missing.py' --file report.md"))
        self.assertEqual((["/abs/fix-swarm.py"], [], False), self.fence('python3 "/abs/fix-swarm.py" --patch /abs/out.patch'))

    def test_env_wrapper_is_skipped(self) -> None:
        self.assertEqual((["/abs/check.py"], [], False), self.fence("/usr/bin/env python3 /abs/check.py"))
        self.assertEqual((["/abs/check.py"], [], False), self.fence("/usr/bin/env -S python3 /abs/check.py"))

    def test_absolute_interpreter_is_not_a_candidate(self) -> None:
        self.assertEqual((["/abs/x.py"], [], False), self.fence("/opt/homebrew/bin/python3 /abs/x.py"))
        self.assertEqual((["/abs/x.py"], [], False), self.fence("/Users/mark/git-projects/ringer/.venv/bin/python /abs/x.py"))

    def test_dash_m_and_dash_c_yield_no_candidate(self) -> None:
        self.assertEqual(([], [], False), self.fence("python3 -m unittest discover -s tests"))
        self.assertEqual(([], [], False), self.fence('sh -c "test -s /abs/x"'))
        self.assertEqual(([], [], False), self.fence("bash -c 'bash /abs/inner.sh'"))

    def test_assignment_prefix_is_skipped(self) -> None:
        self.assertEqual((["/abs/gate.sh"], [], False), self.fence("FOO=1 bash /abs/gate.sh"))
        self.assertEqual((["/abs/check.sh"], [], False), self.fence("PATCH_NAME=step1-fold1 bash /abs/check.sh"))

    def test_redirects_and_operands_are_removed_first(self) -> None:
        self.assertEqual((["/abs/x.py"], [], False), self.fence("python3 /abs/x.py 2>/dev/null"))
        self.assertEqual((["/abs/x.py"], [], False), self.fence("python3 /abs/x.py > /abs/out.log 2>&1"))
        self.assertEqual(([], [], False), self.fence("git diff > /abs/new.patch && test -s /abs/new.patch"))
        self.assertEqual(([], [], False), self.fence("git add -A && git diff --cached > /abs/lane.patch"))

    def test_flag_values_are_never_candidates(self) -> None:
        self.assertEqual((["/abs/fix-swarm.py"], [], False), self.fence("python3 /abs/fix-swarm.py --patch /abs/work/lane.patch"))
        self.assertEqual((["/abs/real.py"], [], False), self.fence("python3 --flag=/abs/notascript /abs/real.py"))

    def test_inline_checks_fence_nothing(self) -> None:
        self.assertEqual(([], [], False), self.fence("test -s out.txt && grep done out.txt"))
        self.assertEqual(([], [], False), self.fence("grep done out.txt || { echo 'FAIL: no done'; exit 1; }"))

    def test_bare_absolute_first_word_is_fenced(self) -> None:
        self.assertEqual((["/abs/checker"], [], False), self.fence("/abs/checker --strict"))
        self.assertEqual(([], [], False), self.fence("checker --strict"), "a bare relative first word is not a candidate")

    def test_glued_operators_split(self) -> None:
        self.assertEqual((["/abs/a.sh", "/abs/b.sh"], [], False), self.fence("bash /abs/a.sh&&bash /abs/b.sh"))
        self.assertEqual((["/abs/a.sh", "/abs/b.sh"], [], False), self.fence("bash /abs/a.sh; bash /abs/b.sh | tail -5"))

    def test_tilde_expands(self) -> None:
        fenced, _, _ = self.fence("python3 ~/checks/x.py")
        self.assertEqual([str(Path("~/checks/x.py").expanduser())], fenced)

    def test_placeholders_yield_nothing(self) -> None:
        self.assertEqual(([], [], False), self.fence("python3 {{KIT_DIR}}/checks/review.py --file report.md"))
        self.assertEqual(([], [], False), self.fence("{{PYTHON}} /abs/x.py"))
        self.assertEqual(([], [], False), self.fence("bash {{CHECK_SCRIPT_PATH}}"))

    def test_relative_candidate_without_cd_is_reported(self) -> None:
        self.assertEqual(([], ["check.py"], False), self.fence("python3 check.py --file report.md"))
        self.assertEqual(([], ["scripts/gate.sh"], False), self.fence("bash scripts/gate.sh"))
        self.assertEqual(([], [], False), self.fence("cd /abs/repo && bash scripts/gate.sh"), "prior cd /abs: silent")
        self.assertEqual(([], ["scripts/gate.sh"], False), self.fence("cd repo && bash scripts/gate.sh"), "cd to a relative dir does not settle it")

    def test_tokenizer_failure_is_flagged_not_fenced(self) -> None:
        fenced, rel, failed = self.fence('bash /abs/x.sh "unterminated')
        self.assertTrue(failed)
        self.assertEqual([], fenced)

    # ---- round-1 panel folds (E1–E7) ----
    def test_e1_env_with_assignments_re_skips_assignments(self) -> None:
        self.assertEqual((["/abs/missing.py"], [], False), self.fence("env FOO=1 python3 /abs/missing.py"))
        self.assertEqual((["/abs/a.py"], [], False), self.fence("env -i PATH=/x python3 /abs/a.py"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("env FOO=1 env BAR=2 bash /abs/a.sh"))

    def test_e2_value_taking_interpreter_options_skip_their_operand(self) -> None:
        self.assertEqual((["/abs/missing.sh"], [], False), self.fence("bash -o pipefail /abs/missing.sh"))
        self.assertEqual((["/abs/check.py"], [], False), self.fence("python3 -W ignore /abs/check.py"))
        self.assertEqual((["/abs/check.py"], [], False), self.fence("python3 -X dev -u /abs/check.py"))
        self.assertEqual(([], [], False), self.fence("python3 -W ignore -m pytest"))
        self.assertEqual((["/abs/a.js"], [], False), self.fence("node -r /abs/setup.js /abs/a.js"))
        self.assertEqual(([], [], False), self.fence("node -e 'require(\"/abs/x\")'"))

    def test_e3_short_option_clusters_with_c_or_m_yield_nothing(self) -> None:
        self.assertEqual(([], [], False), self.fence('bash -lc "/abs/x.sh --y"'))
        self.assertEqual(([], [], False), self.fence("bash -ec 'cd /x && ./y'"))
        self.assertEqual(([], [], False), self.fence("python3 -mpytest -q"))

    def test_e4_grouping_and_newlines(self) -> None:
        self.assertEqual((["/abs/missing.sh"], [], False), self.fence("{ /abs/missing.sh; }"))
        self.assertEqual((["/abs/missing.sh"], [], False), self.fence("(bash /abs/missing.sh)"))
        self.assertEqual(([], [], False), self.fence("(cd /abs && bash gate.sh)"), "a cd inside a group still counts")
        self.assertEqual((["/abs/a.sh", "/abs/b.sh"], [], False), self.fence("bash /abs/a.sh\nbash /abs/b.sh"))
        self.assertEqual((["/abs/a.sh", "/abs/b.sh"], [], False), self.fence("bash /abs/a.sh &&\n  bash /abs/b.sh"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("if bash /abs/a.sh; then echo ok; else exit 1; fi"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("! bash /abs/a.sh"))
        self.assertEqual((["/abs/missing.py"], [], False), self.fence("RESULT=$(cat /abs/x) bash /abs/missing.py"))

    def test_e5_source_dot_exec_are_fenced_like_interpreters(self) -> None:
        self.assertEqual((["/abs/lib.sh"], [], False), self.fence("source /abs/lib.sh && bash -c 'x'"))
        self.assertEqual((["/abs/lib.sh"], [], False), self.fence(". /abs/lib.sh"))
        self.assertEqual((["/abs/run.sh"], [], False), self.fence("exec /abs/run.sh --now"))

    def test_e6_variable_paths_are_neither_fenced_nor_relative(self) -> None:
        for check in ('bash "$HOME/x.sh"', "python3 ${DIR}/x.py", "bash ~someone/x.sh"):
            with self.subTest(check=check):
                fenced, rel, failed = self.fence(check)
                self.assertEqual([], fenced)
                self.assertEqual([], rel, "a variable path is not 'relative' — it is unresolved")
                self.assertFalse(failed)

    def test_e7_fenced_paths_are_deduplicated(self) -> None:
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("bash /abs/a.sh && bash /abs/a.sh"))

    # ---- round-2 panel folds (F1–F5) ----
    def test_f1_noclobber_redirect_target_is_not_fenced(self) -> None:
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("bash /abs/a.sh >|/abs/out.log"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("bash /abs/a.sh >| /abs/out.log 2>&1"))

    def test_f2_env_operand_options_are_skipped(self) -> None:
        self.assertEqual((["/abs/missing.py"], [], False), self.fence("env -u FOO python3 /abs/missing.py"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("env --unset=FOO bash /abs/a.sh"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("env -C /tmp bash /abs/a.sh"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("env --chdir /tmp bash /abs/a.sh"))
        self.assertEqual(([], [], False), self.fence("env -C /abs/repo bash scripts/gate.sh"), "env -C /abs counts as an earlier absolute cd")

    def test_f3_shell_built_paths_are_unresolved_not_fenced(self) -> None:
        for check in ("bash /abs/$RUN/x.sh", "bash /a/*.sh", "bash $(pwd)/a.sh", "bash `echo /abs/b.sh`", "python3 /abs/x[1].py", "bash /abs/?.sh"):
            with self.subTest(check=check):
                fenced, rel, failed = self.fence(check)
                self.assertEqual([], fenced, "a path the shell still has to build is never looked up literally")
                self.assertEqual([], rel)
                self.assertFalse(failed)
                self.assertTrue(analyze_check_fence(check).unresolved, "it is reported as unresolved")

    def test_f4_exec_is_a_wrapper(self) -> None:
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("exec bash /abs/a.sh"))
        self.assertEqual((["/abs/a.py"], [], False), self.fence("exec python3 /abs/a.py"))
        self.assertEqual((["/abs/run.sh"], [], False), self.fence("exec /abs/run.sh --now"))
        self.assertEqual((["/abs/a.sh"], [], False), self.fence("exec env FOO=1 bash /abs/a.sh"))

    def test_f5_heredoc_bodies_are_not_commands(self) -> None:
        self.assertEqual(([], [], False), self.fence("cat <<EOF > /abs/f\nbash /abs/x.sh\nEOF"))
        self.assertEqual((["/abs/first.sh"], [], False), self.fence("bash /abs/first.sh && cat <<'EOF'\n/abs/not-a-script\nEOF"))

    def test_comments_are_stripped_before_tokenising(self) -> None:
        self.assertEqual((["/abs/x.sh"], [], False), self.fence("bash /abs/x.sh  # bash /abs/commented.sh"))


class LintFenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-fence-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / "check.sh"
        self.script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        self.link = self.root / "check-link.sh"
        self.link.symlink_to(self.script)
        (self.root / "adir").mkdir()

    def test_existing_script_no_finding(self) -> None:
        for check in (f"bash {self.script}", f"bash {self.link}", f"FOO=1 sh {self.script} 2>/dev/null"):
            with self.subTest(check=check):
                findings = lint_manifest(manifest_for(task_obj(check)))
                self.assertEqual([], errors(findings) + advisories(findings), findings)

    def test_missing_script_is_an_error_naming_task_and_path(self) -> None:
        missing = self.root / "missing.sh"
        findings = lint_manifest(manifest_for(task_obj(f"sh {missing}")))
        self.assertEqual([f"ERROR: alpha: check script {missing} not found"], errors(findings), findings)

    def test_quoted_missing_script_is_still_caught(self) -> None:
        missing = self.root / "missing.py"
        findings = lint_manifest(manifest_for(task_obj(f"python3 '{missing}' --file report.md")))
        self.assertEqual([f"ERROR: alpha: check script {missing} not found"], errors(findings), findings)

    def test_directory_is_not_a_script(self) -> None:
        adir = self.root / "adir"
        findings = lint_manifest(manifest_for(task_obj(f"bash {adir}")))
        self.assertEqual(1, len(errors(findings)), findings)
        self.assertIn(str(adir), errors(findings)[0])

    def test_stale_output_and_flag_values_are_never_errors(self) -> None:
        check = f"python3 {self.script} --patch {self.root}/not-yet.patch > {self.root}/out.log && cp {self.root}/out.log {self.root}/adir/"
        findings = lint_manifest(manifest_for(task_obj(check)))
        self.assertEqual([], errors(findings), findings)

    def test_relative_script_without_cd_is_advisory_only(self) -> None:
        findings = lint_manifest(manifest_for(task_obj("python3 check.py --file report.md")))
        self.assertEqual([], errors(findings))
        adv = advisories(findings)
        self.assertEqual(1, len(adv), findings)
        self.assertIn("alpha", adv[0])
        self.assertIn("check.py", adv[0])

    def test_relative_script_after_cd_abs_is_silent(self) -> None:
        findings = lint_manifest(manifest_for(task_obj(f"cd {self.root} && bash check.sh")))
        self.assertEqual([], errors(findings) + advisories(findings), findings)

    def test_tokenizer_failure_is_advisory_never_error(self) -> None:
        findings = lint_manifest(manifest_for(task_obj(f'bash {self.script} "unterminated')))
        self.assertEqual([], errors(findings), findings)
        self.assertEqual(1, len(advisories(findings)), findings)

    def test_each_task_is_judged_on_its_own(self) -> None:
        missing = self.root / "missing.sh"
        findings = lint_manifest(
            manifest_for(task_obj(f"bash {self.script}"), task_obj(f"bash {missing}", key="beta"))
        )
        self.assertEqual([f"ERROR: beta: check script {missing} not found"], errors(findings), findings)

    def test_e6_variable_path_gets_its_own_advisory_wording(self) -> None:
        findings = lint_manifest(manifest_for(task_obj('bash "$HOME/x.sh"')))
        self.assertEqual([], errors(findings))
        adv = advisories(findings)
        self.assertEqual(1, len(adv), findings)
        self.assertNotIn("worker's own folder", adv[0])
        self.assertIn("not fenced", adv[0])

    def test_e7_dev_paths_are_never_missing(self) -> None:
        findings = lint_manifest(manifest_for(task_obj("python3 /dev/stdin < /dev/null")))
        self.assertEqual([], errors(findings), findings)

    def test_e1_env_assignment_missing_script_is_an_error(self) -> None:
        missing = self.root / "missing.py"
        findings = lint_manifest(manifest_for(task_obj(f"env FOO=1 python3 {missing}")))
        self.assertEqual([f"ERROR: alpha: check script {missing} not found"], errors(findings), findings)

    def test_f3_shell_built_path_gets_unresolved_advisory_not_error(self) -> None:
        findings = lint_manifest(manifest_for(task_obj("bash /abs/$RUN/x.sh")))
        self.assertEqual([], errors(findings), findings)
        self.assertEqual(1, len(advisories(findings)), findings)
        self.assertIn("not fenced", advisories(findings)[0])

    def test_f1_noclobber_target_is_never_missing(self) -> None:
        findings = lint_manifest(manifest_for(task_obj(f"bash {self.script} >|{self.root}/not-yet.log")))
        self.assertEqual([], errors(findings), findings)

    def test_templates_still_lint_clean(self) -> None:
        for path in sorted((ROOT / "templates").glob("*/manifest*.json")):
            with self.subTest(template=path.name):
                self.assertEqual([], lint_manifest(Manifest.from_path(path)))


class RefusalTests(unittest.TestCase):
    """E1 / E3: `ringer.py run` refuses before any worker launches — nothing on Ringside, zero tokens."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-refuse-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_env = os.environ.copy()
        self.addCleanup(self._restore_env)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["RINGER_HOME"] = str(self.root / "ringer-home")
        self.config_path = self.root / "config.toml"
        self.jsonl_path = self.root / "runs.jsonl"
        self.state_dir = self.root / "state"
        self.config_path.write_text(
            "\n".join(
                [
                    f'state_dir = "{self.state_dir}"',
                    "dashboard_port_base = 18807",
                    "allow_full_access = false",
                    "",
                    "[eval]",
                    'backend = "jsonl"',
                    f'jsonl_path = "{self.jsonl_path}"',
                    "",
                    "[engines.write_done]",
                    'bin = "/bin/sh"',
                    'args_template = ["-c", "printf done > out.txt; echo launched > ' + str(self.root / "worker-launched") + '"]',
                    "sandbox_args = []",
                    "full_access_args = []",
                    'token_regex = "tokens\\\\s+used\\\\s*:?\\\\s*([0-9][0-9,]*)"',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def run_cli(self, command: str, task: dict[str, object]) -> subprocess.CompletedProcess[str]:
        manifest_path = self.root / "m.json"
        manifest_path.write_text(
            json.dumps({"run_name": "gate-refuse", "workdir": str(self.root / "work"), "max_parallel": 1, "tasks": [task]}),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        argv = [sys.executable, "-B", str(RINGER_PATH), "--config", str(self.config_path), command, str(manifest_path)]
        if command == "run":
            argv += ["--identity", "gate-runner", "--no-dashboard"]
        return subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)

    def assert_nothing_ran(self) -> None:
        self.assertFalse((self.root / "worker-launched").exists(), "a worker was launched")
        self.assertFalse((self.root / "work").exists(), "the workdir was created before the refusal")
        self.assertFalse(self.jsonl_path.exists(), "an eval row was written")
        self.assertEqual([], list((self.state_dir / "runs").glob("*.json")) if (self.state_dir / "runs").exists() else [], "a run record was written")

    def test_e1_run_refuses_missing_script_before_launch(self) -> None:
        missing = self.root / "does" / "not" / "exist.sh"
        proc = self.run_cli("run", task_obj(f"sh {missing}", engine="write_done"))
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("alpha", proc.stdout)
        self.assertIn(str(missing), proc.stdout)
        self.assert_nothing_ran()

    def test_e3_quoted_missing_script_refused(self) -> None:
        missing = self.root / "missing.py"
        proc = self.run_cli("run", task_obj(f"python3 '{missing}' --file report.md", engine="write_done"))
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn(str(missing), proc.stdout)
        self.assert_nothing_ran()

    def test_lint_cli_exits_one_with_the_error_line(self) -> None:
        missing = self.root / "missing.sh"
        proc = self.run_cli("lint", task_obj(f"bash {missing}"))
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn(f"lint: ERROR: alpha: check script {missing} not found", proc.stdout)

    def test_existing_script_runs_normally(self) -> None:
        script = self.root / "check.sh"
        script.write_text("#!/bin/sh\ngrep done out.txt || { echo 'FAIL: no done'; exit 1; }\n", encoding="utf-8")
        proc = self.run_cli("run", task_obj(f"sh {script}", engine="write_done", max_attempts=1))
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertTrue((self.root / "worker-launched").exists())
        self.assertTrue(self.jsonl_path.exists())

    def test_relative_advisory_does_not_refuse(self) -> None:
        proc = self.run_cli("run", task_obj("sh check-in-taskdir.sh", engine="write_done", max_attempts=1))
        self.assertIn("advisory:", proc.stdout)
        self.assertTrue((self.root / "worker-launched").exists(), "an advisory must never refuse a run")


if __name__ == "__main__":
    unittest.main()
