"""Bounded ZIP extraction. Only regular Fortran sources are written."""

import io
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from .project import EXCLUDED_DIRS, EXTENSIONS

MAX_UPLOAD = 10_000_000
MAX_EXPANDED = 20_000_000
MAX_SOURCE = 2_000_000
MAX_ENTRIES = 1_000
MAX_SOURCES = 100
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def extract_sources(data: bytes, destination: Path) -> int:
    """Destination must be a fresh, server-owned directory, never user-selected."""
    if len(data) > MAX_UPLOAD:
        raise ValueError("El ZIP supera los 10 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ValueError("El ZIP supera las 1.000 entradas.")
            seen = set()
            expanded = 0
            sources = 0
            for entry in entries:
                raw = entry.orig_filename.rstrip("/")
                parts = raw.split("/")
                if (
                    not raw
                    or len(raw) > 240
                    or "\\" in raw
                    or any(ord(c) < 32 for c in raw)
                    or any(
                        p in {"", ".", ".."}
                        or ":" in p
                        or p.endswith((".", " "))
                        or _RESERVED.match(p)
                        for p in parts
                    )
                    or PurePosixPath(raw).is_absolute()
                ):
                    raise ValueError("El ZIP contiene una ruta no permitida.")
                key = raw.casefold()
                if key in seen:
                    raise ValueError("El ZIP contiene rutas duplicadas o ambiguas.")
                seen.add(key)
                mode = (entry.external_attr >> 16) & 0xFFFF
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ValueError("El ZIP contiene enlaces o archivos especiales.")
                if entry.flag_bits & 1:
                    raise ValueError("No se admiten ZIP cifrados.")
                expanded += entry.file_size
                if expanded > MAX_EXPANDED:
                    raise ValueError("El contenido del ZIP supera los 20 MB.")
                if entry.is_dir() or any(p in EXCLUDED_DIRS for p in parts[:-1]):
                    continue
                path = PurePosixPath(raw)
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                if entry.file_size > MAX_SOURCE:
                    raise ValueError("Una fuente Fortran supera los 2 MB.")
                sources += 1
                if sources > MAX_SOURCES:
                    raise ValueError("El ZIP supera los 100 archivos Fortran.")
                target = destination.joinpath(*parts)
                # Defense in depth in addition to component validation above.
                if not target.resolve().is_relative_to(destination.resolve()):
                    raise ValueError("Ruta fuera del directorio de trabajo.")
                with archive.open(entry) as source:
                    content = source.read(MAX_SOURCE + 1)
                if len(content) > MAX_SOURCE:
                    raise ValueError("Una fuente Fortran supera los 2 MB.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(content)
            if not sources:
                raise ValueError("El ZIP no contiene fuentes Fortran compatibles.")
            return sources
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as exc:
        raise ValueError("ZIP inválido, dañado o con un formato no soportado.") from exc
