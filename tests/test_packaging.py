"""Compare the installed wheel with sources, also in Docker without uv resyncing it."""

from pathlib import Path

import fortran_analyser


def test_installed_python_sources_match_checkout():
    source = Path(__file__).resolve().parents[1] / "backend" / "fortran_analyser"
    installed = Path(fortran_analyser.__file__).resolve().parent
    for path in source.rglob("*.py"):
        relative = path.relative_to(source)
        assert (installed / relative).read_bytes() == path.read_bytes(), str(relative)
