from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_api_dev_defaults_to_stdout_and_keeps_tmp_log_path_unused() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    log_dir = Path(tempfile.mkdtemp(prefix="alicebot-log-smoke-", dir="/tmp"))
    log_path = log_dir / "alicebot-api.log"

    env = os.environ.copy()
    env.update(
        {
            "APP_HOST": "127.0.0.1",
            "APP_PORT": str(port),
            "APP_RELOAD": "false",
            "APP_ENV": "test",
            "APP_LOG_PATH": str(log_path),
            "DATABASE_URL": "postgresql://invalid:invalid@127.0.0.1:1/invalid",
            "REDIS_URL": "redis://alicebot:supersecret@localhost:6379/0",
            "HEALTHCHECK_TIMEOUT_SECONDS": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )

    process = subprocess.Popen(
        ["/bin/bash", str(REPO_ROOT / "scripts" / "api_dev.sh")],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout = ""
    stderr = ""
    try:
        deadline = time.time() + 15
        url = f"http://127.0.0.1:{port}/healthz"

        while time.time() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise AssertionError(
                    "api_dev.sh exited before serving /healthz\n"
                    f"stdout:\n{stdout}\n"
                    f"stderr:\n{stderr}"
                )

            try:
                with request.urlopen(url, timeout=0.5) as response:
                    payload = json.loads(response.read())
                    assert response.status == 503
                    assert payload["status"] == "degraded"
                    break
            except error.HTTPError as exc:
                payload = json.loads(exc.read())
                assert exc.code == 503
                assert payload["status"] == "degraded"
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("Timed out waiting for api_dev.sh to serve /healthz")
    finally:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=5)

    assert not log_path.exists()
    assert "GET /healthz" not in stdout
    assert "GET /healthz" not in stderr
