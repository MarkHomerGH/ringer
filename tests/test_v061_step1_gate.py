#!/usr/bin/env python3
"""v0.6.1 step 1 boss gate — per-task check timeout + `advisory:` + `cause`.

Spec of record: homer-workspace docs/specs/v0.6.1/ringer-scoreboard-truth.md
§4.1 (per-task check timeout, parse-time validation, advisory findings) and
§4.7 (scoreboard truth for non-model failures). Boss-authored; the worker
installs this file byte-for-byte and never edits it.

Contract pinned here (boss rulings for this step, so two builders build the
same thing):
  * TaskSpec.check_timeout_s: int | None, default None (= module default,
    CHECK_TIMEOUT_S, read at call time).
  * Verifier._run_check(command, cwd, timeout_s=None) — positional two-arg
    call keeps working and reads CHECK_TIMEOUT_S at call time.
  * Advisory findings are strings that START with "advisory:" and name the
    task key; they never change lint's exit code.
  * Model-log row field "cause" with values worker-output / check-timeout
    (fence values arrive in step 3). Absent or NULL reads as worker-output.
  * Both aggregators emit "non_model_tasks" (int) per row — the count of
    tasks that had at least one non-worker-output attempt.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import sqlite3
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
    AppConfig,
    ArtifactConfig,
    EvalConfig,
    Manifest,
    TaskSpec,
    aggregate_model_log_rows,
    aggregate_model_scoreboard_rows,
    connect_read_model_db,
    create_read_model_schema,
    db_attempt_rows,
    lint_manifest,
    read_model_column_exists,
    rebuild_read_model_db,
    run_models_command,
    sync_read_model_db,
)

SUITE_RUNNERS = (
    "pytest",
    "unittest",
    "npm test",
    "npm run test",
    "go test",
    "cargo test",
    "make test",
)

LONG_SPEC = (
    "You are a worker in a gate fixture. Create out.txt containing the word done, "
    "in the current working directory, and nothing else. Do not create other files. "
    "Do not modify anything outside the current directory. Print nothing but the "
    "token line the harness expects. This spec is deliberately long enough that "
    "lint's underspecified-spec rule does not fire on it."
)


def task_obj(**overrides: object) -> dict[str, object]:
    obj: dict[str, object] = {
        "key": "alpha",
        "spec": LONG_SPEC,
        "check": "grep done out.txt || { echo 'FAIL: out.txt does not say done'; exit 1; }",
        "expect_files": ["out.txt"],
        "task_type": "probe",
        "verified": "out.txt exists and says done",
    }
    obj.update(overrides)
    return obj


def log_row(
    *,
    run_id: str,
    task_key: str = "task",
    engine: str = "opencode",
    model: str = "openrouter/z-ai/glm-5.2",
    task_type: str = "code-feature",
    verdict: str = "PASS",
    retry: bool = False,
    logged_at: str = "2026-09-24T10:00:00+00:00",
    cause: str | None = None,
    omit_cause: bool = False,
) -> dict[str, object]:
    row: dict[str, object] = {
        "run_id": run_id,
        "task_key": task_key,
        "worker_engine": engine,
        "model": model,
        "task_type": task_type,
        "verdict": verdict,
        "retry": retry,
        "duration_ms": 100,
        "worker_tokens": 200,
        "logged_at": logged_at,
        "orchestrator": "tester",
    }
    if not omit_cause:
        row["cause"] = cause
    return row


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_registry(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "[engines.codex]",
                'default_model = "gpt-5.5"',
                "",
                "[models.\"openrouter/z-ai/glm-5.2\"]",
                'model_display = "GLM 5.2"',
                'lab = "Z.ai (Zhipu AI)"',
                'harness = "OpenCode"',
                'access = "OpenRouter API"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_catalog(path: Path) -> None:
    path.write_text(json.dumps({"models": []}), encoding="utf-8")


# The three-task fixture every aggregator assertion below is computed from.
#   A: attempt 1 check-timeout (TIMEOUT), attempt 2 retry PASS  -> pass, NOT first-try
#   B: attempt 1 PASS worker-output                              -> first-try pass
#   C: attempt 1 check-timeout only                              -> non-model column only
def fixture_rows() -> list[dict[str, object]]:
    return [
        log_row(run_id="r1", task_key="A", verdict="TIMEOUT", cause="check-timeout",
                logged_at="2026-09-24T10:00:00+00:00"),
        log_row(run_id="r1", task_key="A", verdict="PASS", retry=True, cause="worker-output",
                logged_at="2026-09-24T10:01:00+00:00"),
        log_row(run_id="r1", task_key="B", verdict="PASS", cause="worker-output",
                logged_at="2026-09-24T10:02:00+00:00"),
        log_row(run_id="r1", task_key="C", verdict="TIMEOUT", cause="check-timeout",
                logged_at="2026-09-24T10:03:00+00:00"),
    ]


def assert_fixture_numbers(test: unittest.TestCase, row: dict[str, object]) -> None:
    test.assertEqual(2, row["tasks"], row)
    test.assertEqual(2, row["passed"], row)
    test.assertEqual(0, row["failed"], row)
    test.assertEqual(3, row["attempts"], row)
    test.assertAlmostEqual(1.0, float(row["pass_rate"]))
    test.assertAlmostEqual(0.5, float(row["first_try_pass_rate"]))
    test.assertEqual(2, row["non_model_tasks"], row)


class ParseTests(unittest.TestCase):
    def test_check_timeout_s_parses_positive_int(self) -> None:
        task = TaskSpec.from_obj(task_obj(check_timeout_s=5))
        self.assertEqual(5, task.check_timeout_s)

    def test_check_timeout_s_defaults_to_none_meaning_module_default(self) -> None:
        task = TaskSpec.from_obj(task_obj())
        self.assertIsNone(task.check_timeout_s)

    def test_check_timeout_s_rejects_non_positive_int_shapes(self) -> None:
        for bad in ("600", 0, -5, True, 2.5):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError) as ctx:
                    TaskSpec.from_obj(task_obj(check_timeout_s=bad))
                message = str(ctx.exception)
                self.assertIn("alpha", message)
                self.assertIn("check_timeout_s", message)

    def test_bad_check_timeout_s_is_a_parse_error_not_a_lint_finding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ringer-gate-parse-") as tmp:
            manifest_path = Path(tmp) / "bad.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "run_name": "gate-bad",
                        "workdir": str(Path(tmp) / "work"),
                        "tasks": [task_obj(check_timeout_s="600")],
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, "-B", str(RINGER_PATH), "lint", str(manifest_path)],
                cwd=ROOT,
                env={**os.environ, "RINGER_NO_SELF_UPDATE": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
        self.assertEqual(2, proc.returncode, proc.stdout)
        self.assertIn("check_timeout_s", proc.stdout)
        self.assertNotIn("lint: alpha", proc.stdout)


class RunCheckTests(unittest.TestCase):
    def test_explicit_timeout_kills_the_check_and_names_the_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ringer-gate-timeout-") as tmp:
            returncode, timed_out, output = asyncio.run(
                ringer.Verifier._run_check("sleep 5", Path(tmp), timeout_s=1)
            )
        self.assertTrue(timed_out)
        self.assertNotEqual(0, returncode)
        self.assertIn("check timed out after 1s", output)

    def test_explicit_timeout_lets_a_short_check_finish(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ringer-gate-timeout-") as tmp:
            returncode, timed_out, _ = asyncio.run(
                ringer.Verifier._run_check("sleep 1 && exit 0", Path(tmp), timeout_s=5)
            )
        self.assertFalse(timed_out)
        self.assertEqual(0, returncode)

    def test_default_reads_module_constant_at_call_time(self) -> None:
        original = ringer.CHECK_TIMEOUT_S
        ringer.CHECK_TIMEOUT_S = 1
        try:
            with tempfile.TemporaryDirectory(prefix="ringer-gate-timeout-") as tmp:
                _, timed_out, output = asyncio.run(
                    ringer.Verifier._run_check("sleep 5", Path(tmp))
                )
        finally:
            ringer.CHECK_TIMEOUT_S = original
        self.assertTrue(timed_out)
        self.assertIn("check timed out after 1s", output)
        self.assertEqual(60, ringer.CHECK_TIMEOUT_S)


class AdvisoryLintTests(unittest.TestCase):
    def manifest(self, check: str, **task_overrides: object) -> Manifest:
        return Manifest.from_obj(
            {
                "run_name": "gate-lint",
                "workdir": "/tmp/gate-lint",
                "tasks": [task_obj(check=check, **task_overrides)],
            }
        )

    def test_suite_runner_without_budget_is_advisory_only(self) -> None:
        for runner in SUITE_RUNNERS:
            with self.subTest(runner=runner):
                check = f"cd /tmp && {runner} 2>&1 | tail -20; test ${{PIPESTATUS[0]}} = 0"
                findings = lint_manifest(self.manifest(check))
                advisories = [f for f in findings if f.startswith("advisory:")]
                self.assertEqual(1, len(advisories), findings)
                self.assertIn("alpha", advisories[0])
                self.assertIn("check_timeout_s", advisories[0])
                self.assertEqual(findings, advisories, "no non-advisory finding expected")

    def test_suite_runner_with_budget_has_no_advisory(self) -> None:
        check = "cd /tmp && pytest -q 2>&1 | tail -20; test ${PIPESTATUS[0]} = 0"
        findings = lint_manifest(self.manifest(check, check_timeout_s=600))
        self.assertEqual([], [f for f in findings if f.startswith("advisory:")], findings)

    def test_plain_check_has_no_advisory(self) -> None:
        findings = lint_manifest(self.manifest("grep done out.txt || { echo 'FAIL: no done'; exit 1; }"))
        self.assertEqual([], [f for f in findings if f.startswith("advisory:")], findings)

    def _lint_cli(self, tasks: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="ringer-gate-lintcli-") as tmp:
            manifest_path = Path(tmp) / "m.json"
            manifest_path.write_text(
                json.dumps(
                    {"run_name": "gate-lint", "workdir": str(Path(tmp) / "work"), "tasks": tasks}
                ),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, "-B", str(RINGER_PATH), "lint", str(manifest_path)],
                cwd=ROOT,
                env={**os.environ, "RINGER_NO_SELF_UPDATE": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )

    def test_cli_exit_code_is_zero_when_only_advisories(self) -> None:
        proc = self._lint_cli(
            [task_obj(check="cd /tmp && pytest -q 2>&1 | tail -20; test ${PIPESTATUS[0]} = 0")]
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertIn("advisory:", proc.stdout)
        self.assertIn("lint: clean (1 tasks)", proc.stdout)

    def test_cli_exit_code_stays_one_when_a_real_finding_joins_an_advisory(self) -> None:
        proc = self._lint_cli(
            [
                task_obj(check="cd /tmp && pytest -q 2>&1 | tail -20; test ${PIPESTATUS[0]} = 0"),
                task_obj(key="beta", check="true"),
            ]
        )
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("advisory:", proc.stdout)
        self.assertIn("lint: beta", proc.stdout)


class EndToEndCauseTests(unittest.TestCase):
    """Drives `ringer.py run` with a /bin/sh fake worker, as tests/test_ringer.py does."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-e2e-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Isolate the spawned ringer.py from the real ~/.ringer (active-run marker, ringer.db).
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
                    "dashboard_port_base = 18797",
                    "allow_full_access = false",
                    "",
                    "[eval]",
                    'backend = "jsonl"',
                    f'jsonl_path = "{self.jsonl_path}"',
                    "",
                    "[engines.write_done]",
                    'bin = "/bin/sh"',
                    'args_template = ["-c", "printf done > out.txt"]',
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

    def run_manifest(self, name: str, task: dict[str, object], *, extra_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        manifest_path = self.root / f"{name}.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "run_name": name,
                    "workdir": str(self.root / f"work-{name}"),
                    "max_parallel": 1,
                    "tasks": [task],
                }
            ),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        return subprocess.run(
            [
                sys.executable, "-B", str(RINGER_PATH),
                "--config", str(self.config_path),
                "run", str(manifest_path),
                "--identity", "gate-runner",
                "--no-dashboard",
                *extra_args,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
            check=False,
        )

    def rows(self) -> list[dict[str, object]]:
        if not self.jsonl_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_check_timeout_rows_carry_cause_and_name_the_budget(self) -> None:
        proc = self.run_manifest(
            "gate-timeout",
            task_obj(engine="write_done", check="sleep 4; echo 'FAIL: should have been killed'; exit 1", check_timeout_s=1, max_attempts=2),
        )
        rows = self.rows()
        self.assertEqual(2, len(rows), proc.stdout)
        for row in rows:
            self.assertEqual("check-timeout", row.get("cause"), row)
            # The raw check output (with the budget line) rides in the row's notes, as today.
            self.assertIn("check timed out after 1s", str(row.get("notes", "")), row)
            self.assertNotIn("check timed out after 60s", str(row.get("notes", "")), row)
        self.assertIn("gate-timeout", proc.stdout)

    def test_worker_output_rows_carry_cause_on_pass_and_fail(self) -> None:
        self.run_manifest(
            "gate-pass",
            task_obj(engine="write_done", check="sleep 1; grep done out.txt || { echo 'FAIL: no done'; exit 1; }", check_timeout_s=10),
        )
        self.run_manifest(
            "gate-fail",
            task_obj(engine="write_done", check="grep nope out.txt || { echo 'FAIL: no nope'; exit 1; }", max_attempts=1),
        )
        rows = self.rows()
        self.assertEqual(2, len(rows), rows)
        verdicts = {str(row["verdict"]).upper() for row in rows}
        self.assertEqual({"PASS", "FAIL"}, verdicts, rows)
        for row in rows:
            self.assertEqual("worker-output", row.get("cause"), row)


    def test_dry_run_prints_the_budget_only_when_set(self) -> None:
        with_budget = self.run_manifest(
            "gate-dry-set",
            task_obj(engine="write_done", check_timeout_s=7),
            extra_args=("--dry-run",),
        )
        self.assertEqual(0, with_budget.returncode, with_budget.stdout)
        self.assertIn("check_timeout_s: 7", with_budget.stdout)
        without = self.run_manifest(
            "gate-dry-unset",
            task_obj(engine="write_done"),
            extra_args=("--dry-run",),
        )
        self.assertEqual(0, without.returncode, without.stdout)
        # H2: a manifest without the field prints exactly what it printed before this slice.
        self.assertNotIn("check_timeout_s", without.stdout)

    def test_advisory_only_manifest_never_refuses_a_run(self) -> None:
        proc = self.run_manifest(
            "gate-advisory-run",
            task_obj(
                engine="write_done",
                check="cd /tmp && pytest -q 2>&1 | tail -5; test ${PIPESTATUS[0]} = 0",
            ),
            extra_args=("--dry-run",),
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertIn("advisory:", proc.stdout)
        self.assertNotIn("refus", proc.stdout.lower())

    def test_baseline_mode_honours_the_per_task_budget(self) -> None:
        proc = self.run_manifest(
            "gate-baseline",
            task_obj(engine="write_done", check="sleep 4; echo 'FAIL: not killed'; exit 1", check_timeout_s=1, max_attempts=1),
            extra_args=("--baseline",),
        )
        self.assertIn("check timed out after 1s", proc.stdout)
        self.assertNotIn("check timed out after 60s", proc.stdout)
        self.assertEqual([], self.rows(), "baseline mode writes no eval rows")


class ReadModelBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ringer-gate-db-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_env = os.environ.copy()
        self.addCleanup(self.restore_env)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["RINGER_HOME"] = str(self.root / "ringer-home")
        self.log_path = self.root / "runs.jsonl"
        self.db_path = self.root / "ringer.db"
        self.catalog_path = self.root / "catalog.json"
        self.registry_path = self.root / "model-identity.toml"
        write_catalog(self.catalog_path)
        write_registry(self.registry_path)

    def restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def config(self) -> AppConfig:
        return AppConfig(
            path=None,
            identity_default=None,
            state_dir=self.root / "state",
            dashboard_port_base=8787,
            hud_port=8700,
            hud_app_path=None,
            allow_full_access=False,
            eval=EvalConfig(backend="jsonl", jsonl_path=self.log_path),
            engines={},
            artifact=ArtifactConfig(
                enabled=False,
                out_template=str(self.root / "live.html"),
                report_template=str(self.root / "report.html"),
                index_out=self.root / "index.html",
            ),
        )

    def model_args(self, *, log: Path | None = None, db: Path | None = None, json_out: bool = True) -> argparse.Namespace:
        return argparse.Namespace(
            log=log or self.log_path,
            db=db,
            task_type=None,
            model=None,
            engine=None,
            since=None,
            explore=False,
            catalog_file=self.catalog_path,
            notes_file=self.root / "missing-notes.md",
            registry=self.registry_path,
            html=None,
            open=False,
            json=json_out,
        )

    def rebuild(self) -> None:
        rebuild_read_model_db(
            self.db_path,
            self.log_path,
            catalog_path=self.catalog_path,
            registry_path=self.registry_path,
        )


class ReadModelTests(ReadModelBase):
    def test_cause_survives_rebuild_and_select(self) -> None:
        write_jsonl(self.log_path, fixture_rows() + [log_row(run_id="old", task_key="D", omit_cause=True)])
        self.rebuild()
        rows, _ = db_attempt_rows(self.db_path)
        by_task = {}
        for row in rows:
            by_task.setdefault(row["task_key"], []).append(row)
        self.assertEqual("check-timeout", by_task["A"][0]["cause"])
        self.assertEqual("worker-output", by_task["A"][1]["cause"])
        self.assertEqual("worker-output", by_task["B"][0]["cause"])
        self.assertIsNone(by_task["D"][0].get("cause"))
        with sqlite3.connect(self.db_path) as conn:
            self.assertTrue(read_model_column_exists(conn, "attempts", "cause"))
            stored = conn.execute("SELECT cause FROM attempts WHERE task_key = 'D'").fetchone()[0]
            self.assertIsNone(stored)

    def test_cause_survives_incremental_sync(self) -> None:
        write_jsonl(self.log_path, [log_row(run_id="r0", task_key="Z", cause="worker-output")])
        self.rebuild()
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_row(run_id="r1", task_key="A", verdict="TIMEOUT", cause="check-timeout")) + "\n")
        sync_read_model_db(
            self.db_path,
            self.log_path,
            catalog_path=self.catalog_path,
            registry_path=self.registry_path,
        )
        rows, _ = db_attempt_rows(self.db_path)
        causes = {row["task_key"]: row.get("cause") for row in rows}
        self.assertEqual({"Z": "worker-output", "A": "check-timeout"}, causes)

    def test_pre_slice_db_gains_the_cause_column_on_open(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE schema_version (version INTEGER NOT NULL);
                INSERT INTO schema_version (version) VALUES (3);
                PRAGMA user_version = 3;
                CREATE TABLE attempts (
                    id INTEGER PRIMARY KEY,
                    run_id TEXT, task_key TEXT, logged_at TEXT, engine TEXT, model TEXT,
                    reported_model TEXT, expected_model TEXT, reasoning_effort TEXT,
                    task_type TEXT, retry INTEGER, verdict TEXT, duration_ms INTEGER,
                    worker_tokens INTEGER, orchestrator TEXT
                );
                INSERT INTO attempts (run_id, task_key, logged_at, engine, model, task_type, retry, verdict, duration_ms, worker_tokens, orchestrator)
                VALUES ('old', 'legacy', '2026-07-01T00:00:00+00:00', 'opencode', 'openrouter/z-ai/glm-5.2', 'code-feature', 0, 'PASS', 100, 200, 'tester');
                """
            )
        with contextlib.closing(connect_read_model_db(self.db_path)) as conn:
            create_read_model_schema(conn)
            self.assertTrue(read_model_column_exists(conn, "attempts", "cause"))
            conn.commit()
        rows, _ = db_attempt_rows(self.db_path)
        self.assertEqual(1, len(rows))
        self.assertIsNone(rows[0].get("cause"))
        agg = aggregate_model_log_rows(rows)
        self.assertEqual(1, len(agg))
        self.assertEqual(1, agg[0]["tasks"])
        self.assertAlmostEqual(1.0, float(agg[0]["first_try_pass_rate"]))
        self.assertEqual(0, agg[0]["non_model_tasks"])


class AggregatorTests(unittest.TestCase):
    def test_log_aggregator_excludes_non_model_rows_before_choosing_first_and_final(self) -> None:
        agg = aggregate_model_log_rows(fixture_rows())
        self.assertEqual(1, len(agg), agg)
        assert_fixture_numbers(self, agg[0])

    def test_scoreboard_aggregator_matches(self) -> None:
        agg = aggregate_model_scoreboard_rows(fixture_rows())
        self.assertEqual(1, len(agg), agg)
        assert_fixture_numbers(self, agg[0])
        breakdown = {b["task_type"]: b for b in agg[0].get("task_types", [])}
        if "code-feature" in breakdown:
            self.assertAlmostEqual(0.5, float(breakdown["code-feature"]["first_try_pass_rate"]))

    def test_rows_without_cause_are_worker_output_byte_for_byte(self) -> None:
        explicit = [
            log_row(run_id="r1", task_key="A", verdict="FAIL", cause="worker-output",
                    logged_at="2026-09-24T10:00:00+00:00"),
            log_row(run_id="r1", task_key="A", verdict="PASS", retry=True, cause="worker-output",
                    logged_at="2026-09-24T10:01:00+00:00"),
            log_row(run_id="r1", task_key="B", verdict="PASS", cause="worker-output",
                    logged_at="2026-09-24T10:02:00+00:00"),
        ]
        legacy = [dict(row) for row in explicit]
        for row in legacy:
            del row["cause"]
        nulled = [dict(row, cause=None) for row in explicit]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                a, b, c = aggregate(explicit), aggregate(legacy), aggregate(nulled)
                self.assertEqual(a, b)
                self.assertEqual(a, c)
                self.assertEqual(2, a[0]["tasks"])
                self.assertEqual(3, a[0]["attempts"])
                self.assertAlmostEqual(0.5, float(a[0]["first_try_pass_rate"]))
                self.assertEqual(0, a[0]["non_model_tasks"])

    def test_retry_led_group_is_a_pass_not_a_first_try(self) -> None:
        rows = [
            log_row(run_id="r1", task_key="A", verdict="TIMEOUT", cause="check-timeout",
                    logged_at="2026-09-24T10:00:00+00:00"),
            log_row(run_id="r1", task_key="A", verdict="PASS", retry=True, cause="worker-output",
                    logged_at="2026-09-24T10:01:00+00:00"),
        ]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                agg = aggregate(rows)
                self.assertEqual(1, agg[0]["tasks"])
                self.assertEqual(1, agg[0]["passed"])
                self.assertEqual(2, agg[0]["attempts"])
                self.assertAlmostEqual(1.0, float(agg[0]["pass_rate"]))
                self.assertAlmostEqual(0.0, float(agg[0]["first_try_pass_rate"]))
                self.assertEqual(1, agg[0]["non_model_tasks"])


    def test_all_excluded_bucket_is_not_a_scored_row(self) -> None:
        only_excluded = [
            log_row(run_id="r1", task_key="C", verdict="TIMEOUT", cause="check-timeout"),
        ]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                # No model-judged task: no scoreboard row at all — never a 0-task / 0% / probation row.
                self.assertEqual([], aggregate(only_excluded))
        with_one_model_task = only_excluded + [
            log_row(run_id="r1", task_key="B", verdict="PASS", cause="worker-output",
                    logged_at="2026-09-24T10:02:00+00:00"),
        ]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__, case="with-model-task"):
                agg = aggregate(with_one_model_task)
                self.assertEqual(1, len(agg))
                self.assertEqual(1, agg[0]["tasks"])
                self.assertEqual(1, agg[0]["non_model_tasks"])
                self.assertAlmostEqual(1.0, float(agg[0]["first_try_pass_rate"]))

    def test_pre_slice_orphan_retry_pass_keeps_its_first_try(self) -> None:
        # A retry row group_model_log_tasks could not attach (no predecessor) counted as a
        # first-try PASS before this slice; with no non-model rows involved it still must (H2).
        orphan = [log_row(run_id="", task_key="", verdict="PASS", retry=True, omit_cause=True)]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                agg = aggregate(orphan)
                self.assertEqual(1, len(agg))
                self.assertAlmostEqual(1.0, float(agg[0]["first_try_pass_rate"]))
                self.assertEqual(0, agg[0]["non_model_tasks"])

    def test_non_model_head_then_fresh_pass_is_a_first_try(self) -> None:
        # first must be model_rows[0], not ordered[0]: a non-model head followed by a
        # NON-retry worker PASS is a first-try (Hy3 legacy-path A1).
        rows = [
            log_row(run_id="r1", task_key="A", verdict="TIMEOUT", cause="check-timeout",
                    logged_at="2026-09-24T10:00:00+00:00"),
            log_row(run_id="r2", task_key="A", verdict="PASS", cause="worker-output",
                    logged_at="2026-09-24T10:01:00+00:00"),
        ]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                agg = aggregate(rows)
                self.assertEqual(1, len(agg))
                self.assertAlmostEqual(1.0, float(agg[0]["first_try_pass_rate"]))

    def test_mixed_cause_shapes(self) -> None:
        # worker FAIL then check-timeout on the retry: a failed task, 2 attempts, non-model 1.
        rows = [
            log_row(run_id="r1", task_key="A", verdict="FAIL", cause="worker-output",
                    logged_at="2026-09-24T10:00:00+00:00"),
            log_row(run_id="r1", task_key="A", verdict="TIMEOUT", retry=True, cause="check-timeout",
                    logged_at="2026-09-24T10:01:00+00:00"),
        ]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                agg = aggregate(rows)
                self.assertEqual(1, agg[0]["tasks"])
                self.assertEqual(1, agg[0]["failed"])
                self.assertEqual(2, agg[0]["attempts"])
                self.assertEqual(1, agg[0]["non_model_tasks"])
                self.assertAlmostEqual(0.0, float(agg[0]["first_try_pass_rate"]))

    def test_cause_classification_edge_values(self) -> None:
        blank = [log_row(run_id="r1", task_key="A", verdict="PASS", cause="   ")]
        unknown = [log_row(run_id="r1", task_key="A", verdict="PASS", cause="fence-changed")]
        for aggregate in (aggregate_model_log_rows, aggregate_model_scoreboard_rows):
            with self.subTest(aggregate=aggregate.__name__):
                self.assertEqual(1, aggregate(blank)[0]["tasks"], "blank cause reads as worker-output")
                self.assertEqual([], aggregate(unknown), "any cause that is not worker-output is a non-model row")


class ModelsCommandTests(ReadModelBase):
    """Same fixture through `ringer.py models` — default DB path and --log fallback."""

    def test_models_json_on_db_path_carries_non_model_tasks(self) -> None:
        write_jsonl(self.log_path, fixture_rows())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, run_models_command(self.config(), self.model_args(db=self.db_path)))
        payload = json.loads(out.getvalue())
        self.assertEqual(1, len(payload), payload)
        assert_fixture_numbers(self, payload[0])
        self.assertTrue(self.db_path.exists())

    def test_models_json_on_log_fallback_carries_non_model_tasks(self) -> None:
        fixture_log = self.root / "fixture-runs.jsonl"
        write_jsonl(fixture_log, fixture_rows())
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(0, run_models_command(self.config(), self.model_args(log=fixture_log, db=None)))
        payload = json.loads(out.getvalue())
        self.assertEqual(1, len(payload), payload)
        assert_fixture_numbers(self, payload[0])
        self.assertFalse((Path(os.environ["RINGER_HOME"]) / "ringer.db").exists())

    def test_ringside_models_tab_renders_the_shared_column(self) -> None:
        html = ringer.inject_models_tab_into_ringside_html(ringer.read_ringside_html())
        self.assertIn("Non-model", html)

    def test_models_table_shows_a_non_model_column(self) -> None:
        write_jsonl(self.log_path, fixture_rows())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, run_models_command(self.config(), self.model_args(db=self.db_path, json_out=False)))
        self.assertIn("non-model", out.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
