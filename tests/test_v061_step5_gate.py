#!/usr/bin/env python3
"""v0.6.1 step 5 boss gate — Ringside `hud_host` (spec §4.5, ruling 12; §12 X2 / H3; CONTRACT C8).

Boss-authored; the worker installs this file byte-for-byte and never edits it.

Contract pinned here (boss rulings for this step):
  * Config: `[hud] host = "<addr>"` beside `port`, read by `load_hud_host(raw) -> str` next to
    `load_hud_port` (same TOML table); `AppConfig.hud_host: str = DEFAULT_HUD_HOST` where
    `DEFAULT_HUD_HOST = "127.0.0.1"` (a dataclass field WITH a default, appended after the existing
    defaulted fields, so every direct `AppConfig(...)` construction in the byte-locked tests still works).
  * `validate_hud_host(value) -> str` (stdlib `ipaddress` only) returns the literal for a loopback
    address (any 127.0.0.0/8) or a Tailscale address (100.64.0.0/10) and raises ValueError with a
    plain-English, one-sentence message otherwise. The messages are DISTINCT per cause and contain:
      "0.0.0.0"            -> "every interface"           (CONTRACT C8: never 0.0.0.0)
      a LAN / other IPv4   -> "loopback or Tailscale"
      a hostname           -> "not an IPv4 address"
      an IPv6 literal      -> "not an IPv4 address"
    The loader applies it, so a bad config value fails at `AppConfig.load` before anything starts.
  * `hud --host <addr>` is an explicit per-process override, validated the same way. When the flag
    and the config value are BOTH present and differ, `hud` refuses with one sentence naming both
    values (contains "disagree", both literals) before probing or binding. Equal values proceed.
    Neither given -> 127.0.0.1 exactly as today.
  * The EFFECTIVE host steers everything: `PersistentHudServer(..., host=DEFAULT_HUD_HOST)` binds it and
    records it as `server.host`; `hud_is_alive(port, host=DEFAULT_HUD_HOST)` probes
    `http://{host}:{port}/api/runs` (call sites pass `host=` ONLY when the host is not loopback —
    tests/test_hud_single_tab.py monkeypatches `ringer.hud_is_alive` with a one-argument lambda and
    is byte-locked); `ensure_hud_running` probes the configured host, spawns its child with
    `--host <host>` appended to today's argv, and prints `Ringside: http://{host}:{port}`;
    `run_persistent_hud` prints "already running: http://{host}:{port}"; the bind error, the printed
    URL and the post-run "Open it in a browser … (http://…:port)" hint all use the effective host.
  * Bind errors distinguish their cause (errno): EADDRNOTAVAIL -> message contains "is not an
    address on this machine"; EADDRINUSE -> today's "already in use"; any other OSError -> its
    strerror. No server is left running in any refusal case.
  * When the server's recorded `host` is not loopback, GET /api/open-folder responds HTTP 403 with a
    body containing "not available" and runs nothing; the decision keys off `server.host`, never the
    request's Host: header (a spoofed Host: header changes nothing either way).
  * The per-run Dashboard (the second bind site) stays on 127.0.0.1 — untouched.
  * Refusals exit non-zero with the sentence on stderr (main()'s existing "ringer.py: error:" path).
  Round 1 folds (boss-verified): `AppConfig.hud_host_set: bool = False` is True when the config file
    WROTE `[hud] host` (even "127.0.0.1"); the disagreement rule is "flag given AND hud_host_set AND
    flag != config.hud_host", so an explicit loopback config plus `--host 100.x` refuses, and the
    refusal happens before any alive probe (GPT A1 = Sonnet A1). The auto-spawn child inherits the
    parent's config: argv gains `--config <config.path>` right after the script path when config.path
    is not None (Hy3 startup A1 = Sonnet A3); when the 3 s poll ends with no answer the parent prints
    "Ringside did not answer at <url> within 3 s; see <hud.log path>" instead of a bare URL. Refusal
    messages quote the value with repr (Sonnet A4).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from dataclasses import replace as dataclasses_replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RINGER_PATH = ROOT / "ringer.py"
sys.path.insert(0, str(ROOT))

import ringer  # noqa: E402
from ringer import (  # noqa: E402
    DEFAULT_HUD_HOST,
    AppConfig,
    ArtifactConfig,
    EvalConfig,
    PersistentHudServer,
    ensure_hud_running,
    hud_is_alive,
    load_hud_host,
    run_persistent_hud,
    validate_hud_host,
)

TAILNET = "100.64.0.5"


def config(root: Path, host: str | None = None, port: int = 8700) -> AppConfig:
    kwargs = dict(
        path=None,
        identity_default=None,
        state_dir=root / "state",
        dashboard_port_base=8787,
        hud_port=port,
        hud_app_path=None,
        allow_full_access=False,
        eval=EvalConfig(backend="jsonl", jsonl_path=root / "eval.jsonl"),
        engines={},
        artifact=ArtifactConfig(
            enabled=False,
            out_template=str(root / "live.html"),
            report_template=str(root / "report.html"),
            index_out=root / "index.html",
        ),
    )
    if host is not None:
        kwargs["hud_host"] = host
    return AppConfig(**kwargs)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TempMixin:
    def make_root(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="ringer-gate-s5-")
        self.addCleanup(tmp.cleanup)  # type: ignore[attr-defined]
        return Path(tmp.name)


class ValidationTests(unittest.TestCase):
    def test_default_is_loopback(self) -> None:
        self.assertEqual("127.0.0.1", DEFAULT_HUD_HOST)
        self.assertEqual("127.0.0.1", load_hud_host(None))
        self.assertEqual("127.0.0.1", load_hud_host({"port": 8700}))

    def test_accepts_loopback_and_tailscale_literals(self) -> None:
        for value in ("127.0.0.1", "127.0.0.2", "127.255.255.254", "100.64.0.1", "100.108.29.78", "100.127.255.254"):
            with self.subTest(value=value):
                self.assertEqual(value, validate_hud_host(value))
                self.assertEqual(value, load_hud_host({"host": value}))

    def test_refusals_are_distinct_plain_sentences(self) -> None:
        cases = {
            "0.0.0.0": "every interface",
            "192.168.1.10": "loopback or Tailscale",
            "100.128.0.1": "loopback or Tailscale",
            "10.0.0.1": "loopback or Tailscale",
            "homer-studio": "not an IPv4 address",
            "::1": "not an IPv4 address",
            "fd7a:115c::1": "not an IPv4 address",
            "": "not an IPv4 address",
        }
        messages: dict[str, str] = {}
        for value, needle in cases.items():
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    validate_hud_host(value)
                msg = str(ctx.exception)
                self.assertIn(needle, msg)
                if value:
                    self.assertIn(value, msg)
                self.assertLess(msg.count("."), 6, "one sentence, not a paragraph")
                messages[value] = msg
        self.assertEqual(3, len({messages["0.0.0.0"], messages["192.168.1.10"], messages["homer-studio"]}),
                         "the three X2 refusal causes read differently")
        with self.assertRaises(ValueError):
            load_hud_host({"host": "0.0.0.0"})
        with self.assertRaises(ValueError):
            load_hud_host({"host": 8700})

    def test_edge_literals(self) -> None:
        for ok in ("127.0.0.0", "127.255.255.255", "100.64.0.0", "100.127.255.255"):
            with self.subTest(ok=ok):
                self.assertEqual(ok, validate_hud_host(ok))
        for bad in ("100.63.255.255", "100.128.0.0", "0100.64.0.1", " 127.0.0.1", "127.0.0.1 ", "::ffff:127.0.0.1", "localhost", "127.0.0.1\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    validate_hud_host(bad)
                self.assertNotIn("\n", str(ctx.exception), "the refusal is one line even for a value with a newline")

    def test_hud_table_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(f'state_dir = "{tmp}/state"\n[hud]\nhost = "{TAILNET}"\n', encoding="utf-8")
            cfg = AppConfig.load(path)
            self.assertEqual((TAILNET, 8700, True), (cfg.hud_host, cfg.hud_port, cfg.hud_host_set))
            path.write_text(f'state_dir = "{tmp}/state"\n[hud]\n', encoding="utf-8")
            cfg = AppConfig.load(path)
            self.assertEqual(("127.0.0.1", 8700, False), (cfg.hud_host, cfg.hud_port, cfg.hud_host_set))
            path.write_text(f'state_dir = "{tmp}/state"\n[hud]\nhost = "127.0.0.1"\n', encoding="utf-8")
            cfg = AppConfig.load(path)
            self.assertEqual(("127.0.0.1", True), (cfg.hud_host, cfg.hud_host_set), "an explicitly written loopback counts as configured")
        self.assertFalse(config(Path("/tmp/x")).hud_host_set)

    def test_app_config_load_applies_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(f'state_dir = "{tmp}/state"\n[hud]\nport = 8701\nhost = "{TAILNET}"\n', encoding="utf-8")
            cfg = AppConfig.load(path)
            self.assertEqual((TAILNET, 8701), (cfg.hud_host, cfg.hud_port))
            path.write_text(f'state_dir = "{tmp}/state"\n[hud]\nhost = "0.0.0.0"\n', encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                AppConfig.load(path)
            self.assertIn("every interface", str(ctx.exception))
            path.write_text(f'state_dir = "{tmp}/state"\n', encoding="utf-8")
            self.assertEqual("127.0.0.1", AppConfig.load(path).hud_host)

    def test_direct_construction_keeps_working_without_the_field(self) -> None:
        cfg = config(Path("/tmp/x"))
        self.assertEqual("127.0.0.1", cfg.hud_host)


class ProbeAndSpawnTests(TempMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.root = self.make_root()
        self.saved = (ringer.hud_is_alive, ringer.subprocess.Popen, ringer.urllib.request.urlopen, ringer.open_in_browser)

    def tearDown(self) -> None:
        ringer.hud_is_alive, ringer.subprocess.Popen, ringer.urllib.request.urlopen, ringer.open_in_browser = self.saved

    def test_probe_hits_the_given_host_and_defaults_to_loopback(self) -> None:
        urls: list[str] = []

        def fake_urlopen(url, timeout=None):  # type: ignore[no-untyped-def]
            urls.append(str(url))
            raise OSError("closed")

        ringer.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]
        self.assertFalse(hud_is_alive(8700))
        self.assertFalse(hud_is_alive(8700, host=TAILNET))
        self.assertEqual([f"http://127.0.0.1:8700/api/runs", f"http://{TAILNET}:8700/api/runs"], urls)

    def test_h3_configured_host_already_alive_means_no_second_ringside(self) -> None:
        probes: list[tuple[int, str]] = []
        spawned: list[list[str]] = []

        def fake_alive(port, host=DEFAULT_HUD_HOST):  # type: ignore[no-untyped-def]
            probes.append((port, host))
            return True

        ringer.hud_is_alive = fake_alive  # type: ignore[assignment]
        ringer.subprocess.Popen = lambda argv, **k: spawned.append(list(argv))  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ensure_hud_running(config(self.root, host=TAILNET, port=8711), open_browser=True)
        self.assertEqual([], spawned, "a Ringside answering on the configured host means no second one")
        self.assertTrue(probes and all(host == TAILNET for _, host in probes), probes)
        self.assertIn(f"Ringside: http://{TAILNET}:8711", out.getvalue())
        self.assertNotIn("127.0.0.1", out.getvalue())

    def test_auto_spawn_child_receives_the_host_and_the_hint_names_it(self) -> None:
        spawned: list[list[str]] = []
        ringer.hud_is_alive = lambda port, host=DEFAULT_HUD_HOST: False  # type: ignore[assignment]

        class FakeProc:
            pass

        def fake_popen(argv, **kwargs):  # type: ignore[no-untyped-def]
            spawned.append(list(argv))
            return FakeProc()

        ringer.subprocess.Popen = fake_popen  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ensure_hud_running(config(self.root, host=TAILNET, port=8712), open_browser=False)
        self.assertEqual(1, len(spawned), spawned)
        argv = spawned[0]
        self.assertIn("hud", argv)
        self.assertIn("--no-open", argv)
        self.assertEqual("8712", argv[argv.index("--port") + 1])
        self.assertEqual(TAILNET, argv[argv.index("--host") + 1])
        # The probe never answers here, so the line is the no-answer form — still naming the tailnet URL.
        self.assertIn(f"did not answer at http://{TAILNET}:8712", out.getvalue())
        self.assertNotIn("127.0.0.1", out.getvalue())

    def test_loopback_default_spawn_argv_and_probe_are_unchanged_in_shape(self) -> None:
        # The byte-locked single-tab tests patch hud_is_alive with a ONE-argument lambda: the default
        # host must keep calling it with the port alone.
        probes: list[int] = []
        spawned: list[list[str]] = []
        ringer.hud_is_alive = lambda port: probes.append(port) or False  # type: ignore[assignment]
        ringer.subprocess.Popen = lambda argv, **k: spawned.append(list(argv))  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ensure_hud_running(config(self.root, port=8713), open_browser=False)
        self.assertTrue(probes)
        self.assertEqual(1, len(spawned))
        self.assertIn("http://127.0.0.1:8713", out.getvalue())

    def test_spawn_child_inherits_the_parents_config_and_a_silent_spawn_is_reported(self) -> None:
        spawned: list[list[str]] = []
        ringer.hud_is_alive = lambda port, host=DEFAULT_HUD_HOST: False  # type: ignore[assignment]
        ringer.subprocess.Popen = lambda argv, **k: spawned.append(list(argv))  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        cfg_path = self.root / "config.toml"
        cfg_path.write_text(f'state_dir = "{self.root}/state"\n[hud]\nport = 8715\nhost = "{TAILNET}"\n', encoding="utf-8")
        cfg = AppConfig.load(cfg_path)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ensure_hud_running(cfg, open_browser=False)
        argv = spawned[0]
        self.assertEqual(str(cfg_path), argv[argv.index("--config") + 1])
        self.assertLess(argv.index("--config"), argv.index("hud"), "the global --config flag precedes the subcommand")
        self.assertEqual(TAILNET, argv[argv.index("--host") + 1])
        self.assertIn(f"Ringside did not answer at http://{TAILNET}:8715 within 3 s; see {cfg.state_dir / 'hud.log'}", out.getvalue())
        self.assertNotIn(f"Ringside: http://{TAILNET}:8715", out.getvalue())
        # A config with no file path spawns without --config, and the same no-answer line applies.
        spawned.clear()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ensure_hud_running(config(self.root, port=8716), open_browser=False)
        self.assertNotIn("--config", spawned[0])
        self.assertIn("Ringside did not answer at http://127.0.0.1:8716 within 3 s; see ", out.getvalue())

    def test_explicit_loopback_config_plus_tailnet_flag_is_a_disagreement_before_any_probe(self) -> None:
        def never(*a, **k):  # type: ignore[no-untyped-def]
            raise AssertionError("the alive probe must not run before the disagreement refusal")

        ringer.hud_is_alive = never  # type: ignore[assignment]
        cfg = dataclasses_replace(config(self.root, host="127.0.0.1", port=8717), hud_host_set=True)
        with self.assertRaises(ValueError) as ctx:
            run_persistent_hud(cfg, port=None, open_viewer=False, host=TAILNET)
        self.assertIn("disagree", str(ctx.exception))
        self.assertIn(TAILNET, str(ctx.exception))
        self.assertIn("127.0.0.1", str(ctx.exception))
        # Not written in the config: the flag simply wins.
        ringer.hud_is_alive = lambda port, host=DEFAULT_HUD_HOST: True  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = run_persistent_hud(config(self.root, port=8717), port=None, open_viewer=False, host=TAILNET)
        self.assertEqual(0, rc)
        self.assertIn(f"already running: http://{TAILNET}:8717", out.getvalue())
        # Equal values proceed.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = run_persistent_hud(dataclasses_replace(config(self.root, host=TAILNET, port=8718), hud_host_set=True),
                                    port=None, open_viewer=False, host=TAILNET)
        self.assertEqual(0, rc)
        self.assertIn(f"already running: http://{TAILNET}:8718", out.getvalue())

    def test_run_persistent_hud_already_running_names_the_configured_host(self) -> None:
        ringer.hud_is_alive = lambda port, host=DEFAULT_HUD_HOST: True  # type: ignore[assignment]
        ringer.open_in_browser = lambda url: None  # type: ignore[assignment]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = run_persistent_hud(config(self.root, host=TAILNET, port=8714), port=None, open_viewer=False)
        self.assertEqual(0, rc)
        self.assertIn(f"already running: http://{TAILNET}:8714", out.getvalue())


class ServerTests(TempMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.root = self.make_root()
        (self.root / "state").mkdir()
        self.saved_popen = ringer.subprocess.Popen

    def tearDown(self) -> None:
        ringer.subprocess.Popen = self.saved_popen

    def start(self, host: str = DEFAULT_HUD_HOST) -> PersistentHudServer:
        server = PersistentHudServer(self.root / "state", preferred_port=0, open_viewer=False, host=host)
        with contextlib.redirect_stdout(io.StringIO()):
            server.start()
        self.addCleanup(server.stop)
        return server

    def get(self, port: int, path: str, host_header: str | None = None) -> tuple[int, str]:
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
        if host_header:
            req.add_header("Host", host_header)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return int(resp.status), resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            return int(err.code), err.read().decode("utf-8", "replace")

    def test_binds_the_given_host_and_records_it(self) -> None:
        # macOS configures only 127.0.0.1 on lo0, so the recorded-host check runs on that literal;
        # the tailnet path is exercised by setting server.host below and by the EADDRNOTAVAIL case.
        server = self.start("127.0.0.1")
        self.assertEqual("127.0.0.1", server.host)
        self.assertEqual("127.0.0.1", server.httpd.server_address[0])  # type: ignore[union-attr]
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/api/runs", timeout=5) as resp:
            self.assertEqual(200, resp.status)
        self.assertEqual("127.0.0.1", PersistentHudServer(self.root / "state", preferred_port=0, open_viewer=False).host,
                         "the default host is loopback exactly as today")

    def test_open_folder_is_refused_off_loopback_keyed_on_the_bound_host(self) -> None:
        opened: list[list[str]] = []
        ringer.subprocess.Popen = lambda argv, **k: opened.append(list(argv))  # type: ignore[assignment]
        server = self.start()
        # Simulate the tailnet bind: the handler must consult the recorded host, not the Host header.
        server.host = TAILNET
        status, body = self.get(server.port, "/api/open-folder?run=x")  # type: ignore[arg-type]
        self.assertEqual(403, status)
        self.assertIn("not available", body.lower())
        status, body = self.get(server.port, "/api/open-folder?run=x", host_header="127.0.0.1:8700")  # type: ignore[arg-type]
        self.assertEqual(403, status, "a spoofed loopback Host: header does not unlock it")
        self.assertEqual([], opened)
        server.host = "127.0.0.1"
        status, _ = self.get(server.port, "/api/open-folder?run=x", host_header=f"{TAILNET}:8700")  # type: ignore[arg-type]
        if sys.platform == "darwin":
            self.assertEqual(204, status, "on loopback the folder opens even with a spoofed tailnet Host: header")
            self.assertEqual(1, len(opened))
        else:
            self.assertNotEqual(403, status)

    def test_other_bind_errors_carry_their_strerror(self) -> None:
        import errno
        real = ringer.ReusableThreadingHTTPServer

        def boom(*a, **k):  # type: ignore[no-untyped-def]
            raise OSError(errno.EACCES, "Permission denied")

        ringer.ReusableThreadingHTTPServer = boom  # type: ignore[assignment]
        self.addCleanup(lambda: setattr(ringer, "ReusableThreadingHTTPServer", real))
        server = PersistentHudServer(self.root / "state", preferred_port=80, open_viewer=False)
        with self.assertRaises(RuntimeError) as ctx:
            server.start()
        msg = str(ctx.exception)
        self.assertIn("Permission denied", msg)
        self.assertIn("127.0.0.1:80", msg)
        self.assertNotIn("already in use", msg)
        self.assertNotIn("not an address on this machine", msg)
        self.assertIsNone(server.httpd)
        self.assertIsNone(server.thread)

    def test_bind_error_causes_are_distinguished(self) -> None:
        holder = socket.socket()
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        self.addCleanup(holder.close)
        port = int(holder.getsockname()[1])
        server = PersistentHudServer(self.root / "state", preferred_port=port, open_viewer=False)
        with self.assertRaises(RuntimeError) as ctx:
            server.start()
        self.assertIn("already in use", str(ctx.exception))
        self.assertIn(f"127.0.0.1:{port}", str(ctx.exception))
        server = PersistentHudServer(self.root / "state", preferred_port=0, open_viewer=False, host="100.64.0.1")
        with self.assertRaises(RuntimeError) as ctx:
            server.start()
        self.assertIn("is not an address on this machine", str(ctx.exception))
        self.assertIn("100.64.0.1", str(ctx.exception))
        self.assertNotIn("already in use", str(ctx.exception))
        self.assertIsNone(server.thread, "no server thread is left running after a failed bind")


class CliTests(TempMixin, unittest.TestCase):
    """X2 through the real CLI. Every case must exit non-zero before or at bind and leave nothing listening."""

    def setUp(self) -> None:
        self.root = self.make_root()
        self.old_env = os.environ.copy()
        self.addCleanup(self._restore_env)
        os.environ["HOME"] = str(self.root / "home")
        os.environ["RINGER_HOME"] = str(self.root / "ringer-home")
        self.port = free_port()

    def _restore_env(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def write_config(self, hud_host: str | None) -> Path:
        path = self.root / "config.toml"
        lines = [f'state_dir = "{self.root}/state"', "[hud]", f"port = {self.port}"]
        if hud_host:
            lines.append(f'host = "{hud_host}"')
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def hud(self, config_path: Path, *argv: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(RINGER_PATH), "--config", str(config_path), "hud", "--no-open", *argv],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False,
        )

    def assert_nothing_listening(self) -> None:
        with socket.socket() as s:
            self.assertNotEqual(0, s.connect_ex(("127.0.0.1", self.port)), "no server left running")

    def test_x2_three_refusals_before_anything_starts(self) -> None:
        cfg = self.write_config(None)
        for value, needle in (("0.0.0.0", "every interface"), ("192.168.1.10", "loopback or Tailscale"), ("homer-studio", "not an IPv4 address")):
            with self.subTest(value=value):
                proc = self.hud(cfg, "--host", value)
                self.assertNotEqual(0, proc.returncode, proc.stdout)
                self.assertIn(needle, proc.stdout)
                self.assertIn(value, proc.stdout)
                self.assertNotIn("Ringside:", proc.stdout)
                self.assert_nothing_listening()

    def test_x2_in_range_address_not_on_this_machine_fails_at_bind(self) -> None:
        proc = self.hud(self.write_config(None), "--host", "100.64.0.1")
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("is not an address on this machine", proc.stdout)
        self.assertNotIn("already in use", proc.stdout)
        self.assert_nothing_listening()

    def test_x2_flag_and_config_disagree(self) -> None:
        proc = self.hud(self.write_config(TAILNET), "--host", "127.0.0.1")
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("disagree", proc.stdout.lower())
        self.assertIn(TAILNET, proc.stdout)
        self.assertIn("127.0.0.1", proc.stdout)
        self.assertNotIn("Ringside:", proc.stdout)
        self.assert_nothing_listening()

    def test_x2_explicit_loopback_config_plus_tailnet_flag_disagrees(self) -> None:
        proc = self.hud(self.write_config("127.0.0.1"), "--host", TAILNET)
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("disagree", proc.stdout.lower())
        self.assertIn(TAILNET, proc.stdout)
        self.assertNotIn("Ringside:", proc.stdout)
        self.assert_nothing_listening()

    def test_bad_config_host_is_refused_at_load(self) -> None:
        proc = self.hud(self.write_config("0.0.0.0"))
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("every interface", proc.stdout)
        self.assert_nothing_listening()

    def test_help_documents_the_host_flag(self) -> None:
        env = os.environ.copy()
        env["RINGER_NO_SELF_UPDATE"] = "1"
        proc = subprocess.run([sys.executable, "-B", str(RINGER_PATH), "hud", "--help"], cwd=ROOT, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False)
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertIn("--host", proc.stdout)
        self.assertNotIn("bind on 127.0.0.1", proc.stdout, "the --port help no longer hard-codes loopback")


class PostRunHintTests(TempMixin, unittest.TestCase):
    """The end-of-run hint names the configured host (spec §4.5 site :~8754)."""

    def test_hint_uses_the_configured_host(self) -> None:
        root = self.make_root()
        old_env = os.environ.copy()
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old_env)))
        os.environ["HOME"] = str(root / "home")
        os.environ["RINGER_HOME"] = str(root / "ringer-home")
        cfg = root / "config.toml"
        cfg.write_text("\n".join([
            f'state_dir = "{root}/state"', "dashboard_port_base = 18837", "allow_full_access = false",
            "[hud]", "port = 8799", f'host = "{TAILNET}"', "",
            "[eval]", 'backend = "jsonl"', f'jsonl_path = "{root}/runs.jsonl"', "",
            "[engines.write_done]", 'bin = "/bin/sh"', 'args_template = ["-c", "printf done > out.txt"]',
            "sandbox_args = []", "full_access_args = []", 'token_regex = "tokens\\\\s+used\\\\s*:?\\\\s*([0-9][0-9,]*)"', "",
        ]), encoding="utf-8")
        manifest = root / "m.json"
        manifest.write_text(json.dumps({"run_name": "gate-hint", "workdir": str(root / "work"), "max_parallel": 1, "tasks": [{
            "key": "t", "engine": "write_done", "task_type": "probe", "max_attempts": 1, "expect_files": ["out.txt"],
            "check": "grep done out.txt || { echo 'FAIL: no done'; exit 1; }", "verified": "out.txt says done",
            "spec": "You are a worker in a gate fixture. Create out.txt containing the word done, in the current working "
                    "directory. Do not create other files. This spec is long enough for lint's underspecified rule.",
        }]}), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RINGER_NO_SELF_UPDATE"] = "1"
        proc = subprocess.run([sys.executable, "-B", str(RINGER_PATH), "--config", str(cfg), "run", str(manifest),
                               "--identity", "gate", "--no-dashboard"], cwd=ROOT, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False)
        self.assertEqual(0, proc.returncode, proc.stdout)
        self.assertIn(f"http://{TAILNET}:8799", proc.stdout)
        self.assertNotIn("http://127.0.0.1:8700", proc.stdout, "the hint no longer hard-codes loopback:8700")


if __name__ == "__main__":
    unittest.main()
