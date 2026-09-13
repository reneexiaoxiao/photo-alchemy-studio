"""Bounded launcher tests; every spawned service uses a temporary project."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("launch_studio", PROJECT / "scripts" / "launch_studio.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def free_ports():
    for _ in range(50):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port <= 65531 and all(launcher.port_available(p) for p in range(port, port + 5)):
            return tuple(range(port, port + 5))
    raise AssertionError("No temporary port range available")


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "scripts").mkdir()
        for filename in ("studio_server.py", "launch_studio.py"):
            shutil.copyfile(PROJECT / "scripts" / filename, self.root / "scripts" / filename)
        self.ports = free_ports()
        self.children = []

    def tearDown(self):
        for pid, port in self.children:
            # Only a PID returned by our temporary project's live identity is
            # eligible for cleanup; user-running projects are never touched.
            status = launcher.status_at(port, launcher.fingerprint(self.root))
            if status and status.get("pid") == pid:
                os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and launcher.status_at(port, launcher.fingerprint(self.root)):
                time.sleep(0.05)
            self.assertIsNone(launcher.status_at(port, launcher.fingerprint(self.root)))
            for child in launcher._BACKGROUND_PROCESSES:
                if child.pid == pid:
                    child.wait(timeout=2)
            print(f"Launcher lifecycle: temporary PID {pid}, port {port}, stopped after verification.")
        self.temporary.cleanup()

    def cli(self):
        return subprocess.run([sys.executable, str(self.root / "scripts" / "launch_studio.py"), "--no-open", "--port", str(self.ports[0])], cwd=self.root, capture_output=True, text=True, timeout=15)

    def test_detached_cli_process_survives_launcher_exit_and_second_click_reuses_pid(self):
        first = self.cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        state = json.loads((self.root / ".local" / "launcher-state.json").read_text())
        self.children.append((state["pid"], state["port"]))
        self.assertTrue(state["started"])
        self.assertEqual(os.getsid(state["pid"]), state["pid"])
        self.assertIsNotNone(launcher.status_at(state["port"], launcher.fingerprint(self.root)))
        second = self.cli()
        self.assertEqual(second.returncode, 0, second.stderr)
        reused = json.loads((self.root / ".local" / "launcher-state.json").read_text())
        self.assertEqual(reused["pid"], state["pid"])
        self.assertFalse(reused["started"])
        self.assertIn("已找到当前图库", second.stdout)
        self.assertTrue((self.root / ".local" / "studio-server.log").exists())

    def test_different_library_on_first_port_is_left_running(self):
        class OtherLibrary(BaseHTTPRequestHandler):
            def do_GET(handler):
                body = json.dumps({"connected": True, "appId": launcher.APP_ID, "rootFingerprint": "another-project", "pid": os.getpid()}).encode()
                handler.send_response(200)
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
            def log_message(handler, *args):
                pass
        occupied = ThreadingHTTPServer(("127.0.0.1", self.ports[0]), OtherLibrary)
        worker = threading.Thread(target=occupied.serve_forever, daemon=True)
        worker.start()
        try:
            info = launcher.ensure_service(self.root, ports=self.ports, timeout=5)
            self.children.append((info["pid"], info["port"]))
            self.assertEqual(info["port"], self.ports[1])
            self.assertFalse(launcher.port_available(self.ports[0]))
            self.assertIsNone(launcher.status_at(self.ports[0], launcher.fingerprint(self.root)))
        finally:
            occupied.shutdown()
            occupied.server_close()
            worker.join(timeout=2)

    def test_startup_failure_reports_logs_and_offline_fallback(self):
        (self.root / "scripts" / "studio_server.py").write_text("raise SystemExit(2)\n", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("studio-server.log", result.stderr)
        self.assertIn("local.html", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / ".local" / "launcher-state.json").exists())
        self.assertTrue(all(launcher.port_available(port) for port in self.ports))

    def test_private_storage_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".local").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(launcher.LaunchError, "符号链接"):
            launcher.ensure_service(self.root, ports=self.ports, timeout=1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_log_symlink_is_rejected_without_overwrite(self):
        (self.root / ".local").mkdir()
        outside = self.root / "private.txt"
        outside.write_text("UNCHANGED", encoding="utf-8")
        (self.root / ".local" / "studio-server.log").symlink_to(outside)
        with self.assertRaisesRegex(launcher.LaunchError, "符号链接"):
            launcher.ensure_service(self.root, ports=self.ports, timeout=1)
        self.assertEqual(outside.read_text(), "UNCHANGED")

    def test_browser_opener_prefers_tabbit_then_default(self):
        url = "http://127.0.0.1:8796/"
        with patch.object(launcher.sys, "platform", "darwin"), patch.object(Path, "is_dir", return_value=True), patch.object(launcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as execute:
            self.assertTrue(launcher.open_browser(url))
            self.assertEqual(execute.call_args.args[0], ["/usr/bin/open", "-a", "/Applications/Tabbit.app", url])
        with patch.object(launcher.sys, "platform", "darwin"), patch.object(Path, "is_dir", side_effect=[True, False]), patch.object(launcher.subprocess, "run", side_effect=[subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]) as execute:
            self.assertTrue(launcher.open_browser(url))
            self.assertEqual(execute.call_args.args[0], ["/usr/bin/open", url])


if __name__ == "__main__":
    unittest.main(verbosity=2)
