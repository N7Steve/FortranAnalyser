"""Real socket regression: requests must keep working during spawned analyses."""

import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest


def test_real_http_server_stays_responsive_while_analysing():
    with socket.socket() as socket_probe:
        socket_probe.bind(("127.0.0.1", 0))
        port = socket_probe.getsockname()[1]
    with tempfile.TemporaryFile() as logs:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "fortran_analyser.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--loop",
                "fortran_analyser.web:loop_factory",
            ],
            stdout=logs,
            stderr=logs,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3) as client:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        if client.get("/api/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        time.sleep(0.05)
                else:
                    pytest.fail("HTTP server did not start")
                sample = client.get("/api/example")
                response = client.post(
                    "/api/analyses",
                    content=sample.content,
                    headers={"Content-Type": "application/zip"},
                )
                assert response.status_code == 202
                identifier = response.json()["id"]
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    assert client.get("/api/health").json() == {"status": "ok"}
                    job = client.get(f"/api/analyses/{identifier}").json()
                    if job["status"] in {"completed", "failed"}:
                        break
                    time.sleep(0.03)
                assert job["status"] == "completed", job
                report = client.get(f"/api/analyses/{identifier}/report").json()
                assert report["summary"]["files"] == 3
        finally:
            process.terminate()
            process.wait(timeout=10)
