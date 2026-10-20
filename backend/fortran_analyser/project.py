"""Local file discovery and per-file process isolation with resource limits."""

import math
import multiprocessing
import os
from collections.abc import Callable
from pathlib import Path

from fparser import __version__ as parser_version

from .engine import analyse_source
from .models import FileResult, Finding, ProjectResult

EXTENSIONS = {".f", ".for", ".ftn", ".f77", ".f90", ".f95", ".f03", ".f08", ".h90"}
FIXED_EXTENSIONS = {".f", ".for", ".ftn", ".f77"}
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "reference", "__pycache__"}


def _failure(path: str, form: str, rule: str, message: str, status="failed") -> FileResult:
    return FileResult(path, status, form, findings=[Finding(rule, path, 1, "error", message)])


def _worker(connection, source, path, form):
    try:
        connection.send(analyse_source(source, path=path, source_form=form))
    except Exception as exc:
        # Keep unexpected parser failures visible and isolate them from other files.
        connection.send(
            _failure(path, form, "FA104", f"Error interno del parser: {type(exc).__name__}: {exc}")
        )
    finally:
        connection.close()


def _bounded_analysis(source, path, form, timeout):
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(send, source, path, form))
    try:
        process.start()
        send.close()
        if not receive.poll(timeout):
            return _failure(path, form, "FA105", f"Análisis interrumpido: límite de {timeout:g} s.")
        try:
            return receive.recv()
        except EOFError:
            return _failure(path, form, "FA104", "El proceso de análisis terminó sin resultado.")
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join()


def _discover(root: Path):
    if root.is_symlink():
        raise ValueError("No se admiten rutas de entrada simbólicas.")
    if root.is_file():
        if root.suffix.lower() not in EXTENSIONS:
            raise ValueError("La extensión del archivo no está soportada.")
        yield root
        return
    if not root.is_dir():
        raise ValueError(f"No existe la ruta de entrada: {root}")

    def on_error(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=on_error):
        dirs[:] = sorted(
            d for d in dirs if d not in EXCLUDED_DIRS and not (Path(directory) / d).is_symlink()
        )
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() in EXTENSIONS:
                yield path


def analyse_project(
    root: str | Path,
    *,
    source_form: str = "auto",
    max_file_bytes: int = 2_000_000,
    max_files: int = 500,
    timeout: float = 10,
    on_progress: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> ProjectResult:
    """Analyse files sequentially in fresh processes. No project code is run.

    Stable paths and explicit per-file status make the output suitable for a UI.
    Directory errors and exceeding max_files abort instead of silently truncating.
    """
    if source_form not in {"auto", "fixed", "free"}:
        raise ValueError("Formato esperado: auto, fixed o free.")
    if max_file_bytes <= 0 or max_files <= 0 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Los límites deben ser positivos y el tiempo finito.")
    root = Path(root).absolute()
    paths = []
    for path in _discover(root):
        paths.append(path)
        if len(paths) > max_files:
            raise ValueError(f"El proyecto supera el límite de {max_files} archivos Fortran.")
    if not paths:
        raise ValueError("No se encontraron archivos Fortran compatibles.")
    if on_progress:
        on_progress(0, len(paths))
    base = root if root.is_dir() else root.parent
    results = []
    for path in paths:
        if should_cancel and should_cancel():
            raise ValueError("Análisis cancelado.")
        relative = path.relative_to(base).as_posix()
        form = (
            source_form
            if source_form != "auto"
            else ("fixed" if path.suffix.lower() in FIXED_EXTENSIONS else "free")
        )
        if path.is_symlink():
            results.append(
                _failure(relative, form, "FA106", "Enlace simbólico omitido.", "skipped")
            )
            continue
        if not path.is_file():
            results.append(
                _failure(
                    relative,
                    form,
                    "FA106",
                    "No es un archivo regular.",
                    "skipped",
                )
            )
            continue
        try:
            # Bounded read even if a file grows between discovery and opening.
            with path.open("rb") as stream:
                data = stream.read(max_file_bytes + 1)
            if len(data) > max_file_bytes:
                results.append(
                    _failure(
                        relative, form, "FA106", "Archivo superior al límite de tamaño.", "skipped"
                    )
                )
                continue
            source = data.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            results.append(_failure(relative, form, "FA107", f"No se pudo leer como UTF-8: {exc}"))
            continue
        results.append(_bounded_analysis(source, relative, form, timeout))
        if on_progress:
            on_progress(len(results), len(paths))
    if on_progress:
        on_progress(len(results), len(paths))
    summary = {
        status: sum(r.status == status for r in results)
        for status in (
            "ok",
            "partial",
            "failed",
            "skipped",
        )
    }
    summary["files"] = len(results)
    summary["findings"] = sum(len(r.findings) for r in results)
    return ProjectResult("1", "1", f"fparser2 {parser_version} (f2008)", results, summary)
