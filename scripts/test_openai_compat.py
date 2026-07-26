from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class MockChatHandler(BaseHTTPRequestHandler):
    server_version = "SResearcherMock/1.0"

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length) or b"{}")
        if payload.get("model") != "mock-model":
            self.send_error(400, "Unexpected model")
            return

        response: dict[str, Any] = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "OK"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    env = os.environ.copy()
    env.update(
        {
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "mock-model",
            "LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
            "LLM_PROVIDER": "openai",
            "PYTHON_BIN": sys.executable,
        }
    )

    try:
        result = subprocess.run(
            [str(project_root / "researcher.sh"), "--check-api"],
            cwd=project_root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        return result.returncode
    if "API OK:" not in result.stdout:
        print("Error: API preflight did not report success.", file=sys.stderr)
        return 1

    print("OpenAI-compatible API smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
