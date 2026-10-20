"""Container health probe using only Python's standard library."""

import json
import os
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    port = int(os.environ.get("FORTRAN_PORT", "8000"))
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as response:
            return 0 if json.load(response).get("status") == "ok" else 1
    except (OSError, URLError, ValueError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
