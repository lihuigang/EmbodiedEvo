"""Authenticated host transport for macOS simulators and Linux agent containers."""

from __future__ import annotations

import hmac
import json
import os
import secrets
import socket
import subprocess
import sys


def create_tcp_listener(cfg, directory):
    if sys.platform != "darwin" or cfg.simulator.backend != "mujoco_so101":
        return None
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("0.0.0.0", 0))
        listener.listen(8)
        token_path = directory / "transport-token"
        token_path.touch(mode=0o600, exist_ok=False)
        token_path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        (directory / "transport.json").write_text(json.dumps({
            "port": listener.getsockname()[1],
        }))
        return listener
    except BaseException:
        listener.close()
        raise


def docker_transport_args(directory):
    metadata = directory / "transport.json"
    if not metadata.exists():
        return []
    host = os.environ.get("EMBODIEDEVO_AGENT_HOST")
    if not host:
        context = subprocess.run(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout
        host = "host.lima.internal" if "colima" in context else "host.docker.internal"
    port = json.loads(metadata.read_text())["port"]
    return [
        "--env", f"EMBODIEDEVO_TCP_HOST={host}",
        "--env", f"EMBODIEDEVO_TCP_PORT={port}",
        "--env", "EMBODIEDEVO_TOKEN_FILE=/run/embodiedevo/transport-token",
    ]


def authenticate(envelope, token):
    """Unwrap before Session.handle/record_rpc; never put credentials in ledgers."""
    supplied = envelope.get("token") if isinstance(envelope, dict) else None
    if not isinstance(supplied, str) or not hmac.compare_digest(
        supplied.encode("utf-8"), token.encode("utf-8")
    ):
        raise PermissionError("Invalid session token")
    request = envelope.get("request")
    if not isinstance(request, dict):
        raise ValueError("Expected a session request")
    return request
