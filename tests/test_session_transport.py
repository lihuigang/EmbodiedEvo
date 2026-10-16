"""Per-episode authentication and standalone SO-101 clients."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.config import REPO, load_task
from orchestrator.transport import authenticate, create_tcp_listener, docker_transport_args
from scripts import run_codex_so101


class TransportTests(unittest.TestCase):
    def test_authentication_checks_before_exposing_request(self):
        token = "a" * 43
        for envelope in ({}, {"token": "wrong"}, {"token": 1}, {"token": "😎"}):
            with self.subTest(envelope=envelope), self.assertRaises(PermissionError):
                authenticate(envelope, token)
        self.assertEqual(authenticate({"token": token, "request": {"op": "status"}}, token),
                         {"op": "status"})

    def test_tokens_are_unique_private_and_not_part_of_launch_arguments(self):
        cfg = load_task("SO101MuJoCo")
        with tempfile.TemporaryDirectory() as tmp, patch(
            "orchestrator.transport.sys.platform", "darwin"
        ), patch.dict(os.environ, {"EMBODIEDEVO_AGENT_HOST": "host.lima.internal"}):
            tokens = []
            for index in range(2):
                directory = Path(tmp) / str(index)
                directory.mkdir()
                listener = create_tcp_listener(cfg, directory)
                self.addCleanup(listener.close)
                token_path = directory / "transport-token"
                token = token_path.read_text()
                tokens.append(token)
                self.assertGreaterEqual(len(token), 32)
                self.assertEqual(token_path.stat().st_mode & 0o777, 0o600)
                args = docker_transport_args(directory)
                self.assertNotIn(token, " ".join(args))
                self.assertIn("EMBODIEDEVO_TCP_HOST=host.lima.internal", args)
                self.assertNotIn(token, (directory / "transport.json").read_text())
            self.assertNotEqual(*tokens)

    def test_linux_keeps_original_unix_transport(self):
        with patch("orchestrator.transport.sys.platform", "linux"):
            self.assertIsNone(create_tcp_listener(load_task("SO101MuJoCo"), Path("unused")))

    def test_both_standalone_clients_send_authenticated_single_requests(self):
        for task in ("tasks", "tasks_baseline"):
            with self.subTest(task=task), tempfile.TemporaryDirectory() as tmp:
                path = REPO / task / "SO101MuJoCo/Workspace/scripts/env.py"
                spec = importlib.util.spec_from_file_location("standalone_so101", path)
                client = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(client)
                token_file = Path(tmp) / "token"
                token_file.write_text("test-token")
                with socket.socket() as server:
                    server.bind(("127.0.0.1", 0))
                    server.listen()
                    captured = []

                    def respond(captured=captured):
                        server.settimeout(5)
                        connection, _ = server.accept()
                        with connection, connection.makefile("rwb") as stream:
                            captured.append(json.loads(stream.readline()))
                            stream.write(b'{"ok":true}\n')
                            stream.flush()

                    thread = threading.Thread(target=respond)
                    thread.start()
                    with patch.dict(os.environ, {
                        "EMBODIEDEVO_TCP_HOST": "127.0.0.1",
                        "EMBODIEDEVO_TCP_PORT": str(server.getsockname()[1]),
                        "EMBODIEDEVO_TOKEN_FILE": str(token_file),
                    }):
                        self.assertTrue(client.request({"op": "status"})["ok"])
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(captured, [{
                        "token": "test-token", "request": {"op": "status"},
                    }])


class EntrypointTests(unittest.TestCase):
    def test_check_does_not_launch_a_model_or_create_a_run(self):
        with patch.object(run_codex_so101, "preflight", return_value=[]), patch.object(
            run_codex_so101, "run"
        ) as launch:
            self.assertEqual(run_codex_so101.main(["--check"]), 0)
        launch.assert_not_called()

    def test_missing_setup_stops_before_launch(self):
        with (
            patch.object(run_codex_so101, "preflight", return_value=["image missing"]),
            patch.object(run_codex_so101, "run") as launch,
        ):
            self.assertEqual(run_codex_so101.main(["--run-dir", "runs/202610161200_agent"]), 1)
        launch.assert_not_called()

    def test_default_run_launches_five_live_scenes(self):
        with patch.object(run_codex_so101, "preflight", return_value=[]), patch.object(
            run_codex_so101, "run", return_value=0
        ) as launch:
            self.assertEqual(run_codex_so101.main(["--run-dir", "runs/202610161200_agent"]), 0)
        args = launch.call_args.args[0]
        self.assertIn("--viewer", args)
        self.assertEqual(args[args.index("--test-scenes") + 1], "5")


if __name__ == "__main__":
    unittest.main()
