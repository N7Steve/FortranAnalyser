"""Build, exercise and recreate an isolated Docker Compose test project."""

import argparse
import http.client
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18088)
    args = parser.parse_args()
    project = f"fortran-smoke-{uuid.uuid4().hex[:8]}"
    environment = {**os.environ, "FORTRAN_HOST_PORT": f"127.0.0.1:{args.port}"}
    connection = http.client.HTTPConnection("127.0.0.1", args.port, timeout=10)

    def compose(*arguments, capture=False):
        result = subprocess.run(
            ["docker", "compose", "-f", str(ROOT / "compose.yaml"), "-p", project, *arguments],
            cwd=ROOT,
            env=environment,
            check=True,
            text=True,
            capture_output=capture,
        )
        return result.stdout.strip() if capture else None

    def fetch(path, *, data=None, method=None, headers=None):
        connection.request(
            method or ("POST" if data is not None else "GET"),
            path,
            body=data,
            headers=headers or {},
        )
        response = connection.getresponse()
        content = response.read()
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}: {content[:300]!r}")
        return content, response.headers

    def get_json(path):
        return json.loads(fetch(path)[0])

    try:
        print("Building the complete application", flush=True)
        compose("build", "--quiet")
        compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "60")
        html = fetch("/")[0].decode()
        assert "FortranAnalyser" in html
        for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html):
            assert fetch(asset)[0], asset
        assert get_json("/api/config") == {"persistent": True}
        assert (
            json.loads(fetch("/api/health", headers={"Host": "truenas.local:8890"})[0])["status"]
            == "ok"
        )
        data = fetch("/api/example")[0]
        job = json.loads(
            fetch(
                "/api/analyses?name=Docker%20validation",
                data=data,
                headers={"Content-Type": "application/zip"},
            )[0]
        )
        identifier = job["id"]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            assert get_json("/api/health")["status"] == "ok"
            job = get_json(f"/api/analyses/{identifier}")
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.1)
        assert job["status"] == "completed", job
        report = get_json(f"/api/analyses/{identifier}/report")
        assert report["summary"]["files"] == 3
        assert report["summary"]["ok"] == 2
        assert report["summary"]["partial"] == 1
        source_url = f"/api/analyses/{identifier}/source?path=example/model.f90"
        source = get_json(source_url)
        assert "module transport_model" in source["content"]
        downloaded, headers = fetch(f"/api/analyses/{identifier}/report?download=true")
        assert json.loads(downloaded) == report and "attachment" in headers["Content-Disposition"]
        container = compose("ps", "-q", capture=True)
        inspection = json.loads(
            subprocess.check_output(["docker", "inspect", container], text=True)
        )[0]
        assert inspection["Config"]["User"] == "568:568"
        assert inspection["HostConfig"]["ReadonlyRootfs"]
        compose("exec", "-T", "fortran-analyser", "python", "-m", "fortran_analyser.healthcheck")
        compose(
            "exec",
            "-T",
            "fortran-analyser",
            "python",
            "-c",
            "import shutil; from pathlib import Path; "
            "assert shutil.which('node') is None; assert shutil.which('npm') is None; "
            "assert shutil.which('uv') is None; assert not Path('/app/reference').exists()",
        )
        print("Recreating the container while keeping the data volume", flush=True)
        connection.close()
        compose("up", "-d", "--no-build", "--force-recreate", "--wait", "--wait-timeout", "60")
        assert get_json(f"/api/analyses/{identifier}")["status"] == "completed"
        assert get_json(f"/api/analyses/{identifier}/report") == report
        assert get_json(source_url) == source
        assert json.loads(fetch(f"/api/analyses/{identifier}", method="DELETE")[0])["deleted"]
        output = ROOT / "reports" / "docker-validation.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "platform": inspection["Platform"],
                    "image": inspection["Image"],
                    "user": inspection["Config"]["User"],
                    "read_only": True,
                    "persistence_after_recreate": True,
                    "report_summary": report["summary"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: web, API, export, non-root execution and persistence after recreation",
            flush=True,
        )
    except BaseException:
        compose("logs", "--tail=60")
        raise
    finally:
        connection.close()
        # A random project name guarantees these are only our synthetic test resources.
        compose("down", "--volumes", "--remove-orphans", "--rmi", "local")


if __name__ == "__main__":
    main()
