#!/usr/bin/env python3
"""v0.6.1 step 3 boss gate — mid-run integrity fence (spec §4.3, ruling 6).

Boss-authored; the worker installs this file byte-for-byte and never edits it.

Contract pinned here (boss rulings for this step):
  * `CheckScriptFingerprint` frozen dataclass: path (as written, expanded), resolved (symlinks
    followed), size (int), mtime_ns (int), sha256 (hex of the content the path resolves to);
    `fingerprint_check_script(path: str) -> CheckScriptFingerprint | None` (None when missing).
  * At run start (after lint, before the first worker) the run state JSON gains
    `"check_fences": {<task_key>: [fingerprint dicts...]}` — one entry per fenced path of that
    task (from analyze_check_fence(...).fenced); tasks with no fenced path get an empty list.
  * Immediately before each check execution the task's fenced paths are re-fingerprinted; on
    any difference the check is NOT executed and the attempt is a FAIL whose raw output contains
    exactly one of:
      "[ringer.py] check script changed since run start: <path> (expected <8 hex>, found <8 hex>); restart the run"
      "[ringer.py] check script missing at check time: <path> (present at run start); restart the run"
  * `VerifyResult.terminal: bool = False`; a fence FAIL sets it True and the retry branch never
    schedules attempt 2. The model-log row carries cause "fence-changed" / "fence-missing" and a
    verify_method that is NOT "executed-check" (pinned: "check-not-executed").
  * Tasks whose checks already ran keep their results. No override exists.
"""
from __future__ import annotations

import dataclasses
import hashlib
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
from ringer import (  # noqa: E402
    CheckScriptFingerprint,
    VerifyResult,
    aggregate_model_log_rows,
    aggregate_model_scoreboard_rows,
    fingerprint_check_script,
)

LONG_SPEC = (
    "You are a worker in a gate fixture. Create out.txt containing the word done, in the current "
    "working directory. Do not create other files. This spec is deliberately long enough that "
    "lint's underspecified-spec rule does not fire on it."
)


class FingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-fp-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / "check.sh"
        self.script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    def test_fingerprint_fields(self) -> None:
        fp = fingerprint_check_script(str(self.script))
        assert fp is not None
        self.assertTrue(dataclasses.is_dataclass(fp))
        self.assertIsInstance(fp, CheckScriptFingerprint)
        self.assertEqual(str(self.script), fp.path)
        self.assertEqual(str(self.script.resolve()), fp.resolved)
        self.assertEqual(self.script.stat().st_size, fp.size)
        self.assertEqual(self.script.stat().st_mtime_ns, fp.mtime_ns)
        self.assertEqual(hashlib.sha256(self.script.read_bytes()).hexdigest(), fp.sha256)

    def test_missing_is_none(self) -> None:
        self.assertIsNone(fingerprint_check_script(str(self.root / "nope.sh")))

    def test_symlink_hashes_the_target_and_a_swap_changes_it(self) -> None:
        link = self.root / "link.sh"
        link.symlink_to(self.script)
        before = fingerprint_check_script(str(link))
        assert before is not None
        self.assertEqual(str(self.script.resolve()), before.resolved)
        other = self.root / "other.sh"
        other.write_text("#!/bin/sh\necho swapped\n", encoding="utf-8")
        link.unlink()
        link.symlink_to(other)
        after = fingerprint_check_script(str(link))
        assert after is not None
        self.assertNotEqual(before.sha256, after.sha256)
        self.assertEqual(str(other.resolve()), after.resolved)

    def test_tilde_is_expanded(self) -> None:
        home = self.root / "home"
        home.mkdir()
        (home / "c.sh").write_text("x\n", encoding="utf-8")
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            fp = fingerprint_check_script("~/c.sh")
        finally:
            if old is not None:
                os.environ["HOME"] = old
        assert fp is not None
        self.assertEqual(str(home / "c.sh"), fp.path)

    def test_verify_result_terminal_defaults_false(self) -> None:
        v = VerifyResult(ok=False, check_returncode=None, check_timed_out=False, raw_output_excerpt="")
        self.assertFalse(v.terminal)


class MidRunFenceTests(unittest.TestCase):
    """X1 / H4 as subprocess tests: a fake /bin/sh worker edits or deletes the shared script mid-run."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-fence-run-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_env = os.environ.copy()
        self.addCleanup(self._restore_env)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["RINGER_HOME"] = str(self.root / "ringer-home")
        self.config_path = self.root / "config.toml"
        self.jsonl_path = self.root / "runs.jsonl"
        self.state_dir = self.root / "state"
        self.script = self.root / "gate.sh"
        self.script.write_text("#!/bin/sh\ngrep done out.txt || { echo 'FAIL: no done'; exit 1; }\n", encoding="utf-8")
        engines = {
            "write_done": "printf done > out.txt",
            "edit_script": f"printf '\\n# tampered\\n' >> {self.script}; printf done > out.txt",
            "delete_script": f"rm -f {self.script}; printf done > out.txt",
            "rewrite_patch": f"printf 'new patch body\\n' > {self.root}/lane.patch; printf done > out.txt",
            "touch_script": f"sleep 1; touch {self.script}; printf done > out.txt",
            "swap_link": f"cp {self.script} {self.root}/copy.sh; rm -f {self.root}/link.sh; ln -s {self.root}/copy.sh {self.root}/link.sh; printf done > out.txt",
            "hang_and_edit": f"printf '\\n# tampered\\n' >> {self.script}; sleep 30",
        }
        lines = [
            f'state_dir = "{self.state_dir}"',
            "dashboard_port_base = 18817",
            "allow_full_access = false",
            "",
            "[eval]",
            'backend = "jsonl"',
            f'jsonl_path = "{self.jsonl_path}"',
            "",
        ]
        for name, cmd in engines.items():
            lines += [
                f"[engines.{name}]",
                'bin = "/bin/sh"',
                f'args_template = ["-c", {json.dumps(cmd)}]',
                "sandbox_args = []",
                "full_access_args = []",
                'token_regex = "tokens\\\\s+used\\\\s*:?\\\\s*([0-9][0-9,]*)"',
                "",
            ]
        self.config_path.write_text("\n".join(lines), encoding="utf-8")

    def _restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def task(self, key: str, engine: str, check: str, **overrides: object) -> dict[str, object]:
        obj: dict[str, object] = {
            "key": key,
            "spec": LONG_SPEC,
            "check": check,
            "expect_files": ["out.txt"],
            "engine": engine,
            "task_type": "probe",
            "verified": "out.txt says done",
        }
        obj.update(overrides)
        return obj

    def run_manifest(self, name: str, tasks: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
        manifest_path = self.root / f"{name}.json"
        manifest_path.write_text(
            json.dumps({"run_name": name, "workdir": str(self.root / f"work-{name}"), "max_parallel": 1, "tasks": tasks}),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(RINGER_PATH), "--config", str(self.config_path), "run", str(manifest_path),
             "--identity", "gate-runner", "--no-dashboard"],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False,
        )

    def rows(self) -> list[dict[str, object]]:
        if not self.jsonl_path.exists():
            return []
        return [json.loads(l) for l in self.jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def state(self) -> dict[str, object]:
        files = sorted((self.state_dir / "runs").glob("*.json"))
        self.assertEqual(1, len(files), files)
        return json.loads(files[0].read_text(encoding="utf-8"))

    def test_run_state_records_the_fingerprint(self) -> None:
        proc = self.run_manifest("gate-fp", [
            self.task("scripted", "write_done", f"sh {self.script}", max_attempts=1),
            self.task("inline", "write_done", "grep done out.txt || { echo 'FAIL: no done'; exit 1; }", max_attempts=1),
        ])
        self.assertEqual(0, proc.returncode, proc.stdout)
        fences = self.state().get("check_fences")
        self.assertIsInstance(fences, dict, "run state JSON must carry check_fences")
        assert isinstance(fences, dict)
        self.assertEqual([], fences.get("inline"), "an inline check has nothing to fence")
        entries = fences.get("scripted")
        assert isinstance(entries, list) and len(entries) == 1, fences
        entry = entries[0]
        self.assertEqual(str(self.script), entry["path"])
        self.assertEqual(str(self.script.resolve()), entry["resolved"])
        self.assertEqual(hashlib.sha256(self.script.read_bytes()).hexdigest(), entry["sha256"])
        self.assertEqual(self.script.stat().st_size, entry["size"])
        self.assertIn("mtime_ns", entry)
        for row in self.rows():
            self.assertEqual("worker-output", row.get("cause"), row)
            self.assertEqual("PASS", str(row["verdict"]).upper(), row)

    def test_x1_script_edited_mid_run(self) -> None:
        expected8 = hashlib.sha256(self.script.read_bytes()).hexdigest()[:8]
        proc = self.run_manifest("gate-x1", [
            self.task("first", "write_done", f"sh {self.script}", max_attempts=1),
            self.task("tamper", "edit_script", f"sh {self.script}", max_attempts=2),
            self.task("third", "write_done", f"sh {self.script}", max_attempts=2),
        ])
        rows = self.rows()
        by_key: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            by_key.setdefault(str(row["task_key"]), []).append(row)
        # Earlier PASS stands.
        self.assertEqual(["PASS"], [str(r["verdict"]).upper() for r in by_key["first"]])
        self.assertEqual("worker-output", by_key["first"][0].get("cause"))
        # The tampering task: exactly ONE attempt despite max_attempts 2, FAIL, fence-changed.
        self.assertEqual(1, len(by_key["tamper"]), by_key["tamper"])
        tamper = by_key["tamper"][0]
        self.assertEqual("FAIL", str(tamper["verdict"]).upper(), tamper)
        self.assertEqual("fence-changed", tamper.get("cause"), tamper)
        self.assertNotEqual("executed-check", tamper.get("verify_method"), tamper)
        found8 = hashlib.sha256(self.script.read_bytes()).hexdigest()[:8]
        reason = f"[ringer.py] check script changed since run start: {self.script} (expected {expected8}, found {found8}); restart the run"
        self.assertIn(reason, str(tamper.get("notes", "")), tamper)
        # The third task's script is still the tampered one: also a fence FAIL, no retry, and the
        # scoreboard never sees a model failure for it.
        self.assertEqual(1, len(by_key["third"]), by_key["third"])
        self.assertEqual("fence-changed", by_key["third"][0].get("cause"))
        self.assertIn("restart the run", proc.stdout)
        # Scoreboard truth: 'first' (write_done engine) is the only model-judged task; 'third'
        # (same engine) counts only in non-model; 'tamper' sits under a different engine with no
        # model-judged task at all, so under the step-1 F1 ruling it has no row — it is NEVER
        # attributed to another bucket.
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            agg = aggregate(rows)
            self.assertEqual(1, len(agg), agg)
            self.assertEqual("write_done", agg[0]["engine"])
            self.assertEqual(1, agg[0]["tasks"], "only the first task is model-judged")
            self.assertEqual(1, agg[0]["non_model_tasks"])
            self.assertAlmostEqual(1.0, float(agg[0]["first_try_pass_rate"]))

    def test_x1_variant_script_deleted_mid_run(self) -> None:
        proc = self.run_manifest("gate-x1-del", [
            self.task("first", "write_done", f"sh {self.script}", max_attempts=1),
            self.task("deleter", "delete_script", f"sh {self.script}", max_attempts=2),
        ])
        rows = [r for r in self.rows() if r["task_key"] == "deleter"]
        self.assertEqual(1, len(rows), rows)
        self.assertEqual("FAIL", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("fence-missing", rows[0].get("cause"), rows[0])
        self.assertNotEqual("executed-check", rows[0].get("verify_method"), rows[0])
        reason = f"[ringer.py] check script missing at check time: {self.script} (present at run start); restart the run"
        self.assertIn(reason, str(rows[0].get("notes", "")), rows[0])
        self.assertIn("restart the run", proc.stdout)

    def test_h4_stale_output_rewritten_by_the_check_is_not_tampering(self) -> None:
        patch = self.root / "lane.patch"
        patch.write_text("old patch body\n", encoding="utf-8")
        check = f"sh {self.script} && cp out.txt {patch} && test -s {patch}"
        proc = self.run_manifest("gate-h4", [
            self.task("lane", "rewrite_patch", check, max_attempts=1),
        ])
        self.assertEqual(0, proc.returncode, proc.stdout)
        fences = self.state()["check_fences"]
        self.assertEqual([str(self.script)], [e["path"] for e in fences["lane"]], "only the script is fenced, never the --patch/output path")
        rows = self.rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("PASS", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("worker-output", rows[0].get("cause"))
        self.assertNotIn("restart the run", proc.stdout)

    # ---- round-1 panel folds (H1–H3) + gate hardenings ----
    def test_h1_symlink_swapped_to_identical_content_is_a_change(self) -> None:
        link = self.root / "link.sh"
        link.symlink_to(self.script)
        rows_before = self.rows()
        self.run_manifest("gate-h1", [self.task("swap", "swap_link", f"sh {link}", max_attempts=2)])
        rows = [r for r in self.rows() if r["task_key"] == "swap"]
        self.assertEqual(1, len(rows), rows)
        self.assertEqual("FAIL", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("fence-changed", rows[0].get("cause"), rows[0])
        self.assertIn("check script changed since run start", str(rows[0].get("notes", "")), rows[0])

    def test_h2_worker_failure_wins_over_a_tripped_fence_for_cause(self) -> None:
        self.run_manifest("gate-h2", [self.task("hang", "hang_and_edit", f"sh {self.script}", timeout_s=2, max_attempts=2)])
        rows = [r for r in self.rows() if r["task_key"] == "hang"]
        self.assertEqual(1, len(rows), "a tripped fence still ends the task — no attempt 2")
        self.assertEqual("TIMEOUT", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("worker-output", rows[0].get("cause"), "the worker's own failure is the model's — never hidden behind the fence")
        self.assertEqual("check-not-executed", rows[0].get("verify_method"), rows[0])
        self.assertIn("restart the run", str(rows[0].get("notes", "")), rows[0])

    def test_h3_dev_paths_are_never_fenced(self) -> None:
        proc = self.run_manifest("gate-h3", [self.task("devnull", "write_done", "sh /dev/null && grep done out.txt", max_attempts=1)])
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertEqual([], self.state()["check_fences"]["devnull"])
        rows = self.rows()
        self.assertEqual("PASS", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("worker-output", rows[0].get("cause"))

    def test_mtime_only_touch_does_not_trip_the_fence(self) -> None:
        proc = self.run_manifest("gate-touch", [self.task("touch", "touch_script", f"sh {self.script}", max_attempts=1)])
        self.assertEqual(0, proc.returncode, proc.stdout)
        rows = self.rows()
        self.assertEqual("PASS", str(rows[0]["verdict"]).upper(), rows[0])
        self.assertEqual("worker-output", rows[0].get("cause"))
        self.assertNotIn("restart the run", proc.stdout)

    def test_untouched_script_across_retry_is_unaffected(self) -> None:
        failing = self.root / "failing.sh"
        failing.write_text("#!/bin/sh\necho 'FAIL: always'; exit 1\n", encoding="utf-8")
        self.run_manifest("gate-retry", [self.task("retry", "write_done", f"sh {failing}", max_attempts=2)])
        rows = self.rows()
        self.assertEqual(2, len(rows), "an ordinary FAIL still retries")
        for row in rows:
            self.assertEqual("worker-output", row.get("cause"), row)
            self.assertEqual("executed-check", row.get("verify_method"), row)


if __name__ == "__main__":
    unittest.main()
