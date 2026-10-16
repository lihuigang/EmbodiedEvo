"""Standalone standard-library client for one persistent EmbodiedEvo session."""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

MAX_MESSAGE = 16 * 1024 * 1024


def receive(stream):
    line = stream.readline(MAX_MESSAGE + 1)
    if not line or len(line) > MAX_MESSAGE or not line.endswith(b"\n"):
        raise ConnectionError("Incomplete response; do not retry an action automatically")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def request(payload):
    host = os.environ.get("EMBODIEDEVO_TCP_HOST")
    if host:
        token = Path(os.environ["EMBODIEDEVO_TOKEN_FILE"]).read_text().strip()
        payload = {"token": token, "request": payload}
        connection = socket.create_connection((host, int(os.environ["EMBODIEDEVO_TCP_PORT"])), 10)
        connection.settimeout(None)
    else:
        address = os.environ.get("EMBODIEDEVO_SOCKET")
        if not address:
            raise RuntimeError("EMBODIEDEVO_SOCKET is not set")
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.connect(address)
        except BaseException:
            connection.close()
            raise
    with connection:
        data = json.dumps(payload, ensure_ascii=True).encode() + b"\n"
        if len(data) > MAX_MESSAGE:
            raise ValueError("Session message exceeds 16 MiB")
        with connection.makefile("rwb") as stream:
            stream.write(data)
            stream.flush()
            return receive(stream)


def source_snapshot(entry, includes):
    workspace = Path(os.environ.get("EMBODIEDEVO_WORKSPACE", Path(__file__).parents[1])).resolve()
    files = []
    for name in [*includes, entry]:
        path = (workspace / name).resolve()
        relative = path.relative_to(workspace)
        if relative.parts[0] not in {"submission", "skills"} or path.suffix != ".py":
            raise ValueError("Submit .py files inside submission/ or skills/")
        files.append({"path": str(relative), "code": path.read_text(encoding="utf-8")})
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    execute = sub.add_parser("exec")
    execute.add_argument("file", nargs="?", default="submission/solution.py")
    execute.add_argument("--include", action="append", default=[])
    for command in ("status", "observe", "instruction", "reset", "finish"):
        sub.add_parser(command)
    args = parser.parse_args(argv)
    payload = {"op": args.command}
    try:
        if args.command == "exec":
            payload["files"] = source_snapshot(args.file, args.include)
        result = request(payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", False) else 1
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
