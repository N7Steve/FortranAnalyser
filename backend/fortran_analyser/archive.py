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


def _extract_zip(data: bytes, destination: Path) -> int:
    """Destination must be a fresh, server-owned directory, never user-selected."""
    if len(data) > MAX_EXPANDED + 1_000_000:
        raise ValueError("El ZIP normalizado supera el límite.")
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


def extract_sources(data: bytes, destination: Path, filename: str = "source.f90.gz") -> int:
    """Recognize by signature; normalize bounded streams through the ZIP validator."""
    import bz2
    import gzip
    import lzma
    import tarfile

    import py7zr

    if len(data) > MAX_UPLOAD:
        raise ValueError("El archivo comprimido supera los 10 MB.")
    if zipfile.is_zipfile(io.BytesIO(data)):
        return _extract_zip(data, destination)
    try:
        output = io.BytesIO()
        expanded = 0
        entries = 0
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as normalized:

            def add(name, content):
                nonlocal expanded, entries
                expanded += len(content)
                entries += 1
                if expanded > MAX_EXPANDED:
                    raise ValueError("El contenido supera los 20 MB.")
                if entries > MAX_ENTRIES:
                    raise ValueError("El archivo supera las 1.000 entradas.")
                normalized.writestr(name, content)

            if py7zr.is_7zfile(io.BytesIO(data)):
                from py7zr.io import WriterFactory

                class Sink(io.BytesIO):
                    def write(self, chunk):
                        nonlocal expanded
                        expanded += len(chunk)
                        if expanded > MAX_EXPANDED:
                            raise ValueError("El contenido supera los 20 MB.")
                        return super().write(chunk)

                    def close(self):
                        pass  # py7zr closes writers; retain bounded buffers until normalization.

                    def size(self):
                        return len(self.getbuffer())

                class Factory(WriterFactory):
                    def __init__(self):
                        self.streams = {}

                    def create(self, name):
                        stream = Sink()
                        self.streams[name] = stream
                        return stream

                with py7zr.SevenZipFile(io.BytesIO(data)) as archive:
                    if archive.needs_password():
                        raise ValueError("No se admiten archivos cifrados.")
                    members = archive.files
                    if len(members) > MAX_ENTRIES:
                        raise ValueError("El archivo supera las 1.000 entradas.")
                    if sum(m.uncompressed for m in members) > MAX_EXPANDED:
                        raise ValueError("El contenido supera los 20 MB.")
                    for member in members:
                        if member.is_symlink or member.is_junction or member.is_socket:
                            raise ValueError("El archivo contiene enlaces o archivos especiales.")
                    # Validate all names before decompression, including directories.
                    check = io.BytesIO()
                    with zipfile.ZipFile(check, "w") as probe:
                        for member in members:
                            probe.writestr(member.filename.rstrip("/") + "/", b"")
                    # Validation only; no source will be emitted from directory entries.
                    try:
                        _extract_zip(check.getvalue(), destination)
                    except ValueError as exc:
                        if "no contiene fuentes" not in str(exc):
                            raise
                    factory = Factory()
                    archive.extractall(factory=factory)
                    expanded = 0
                    for name, stream in factory.streams.items():
                        add(name, stream.getvalue())
            else:
                decoded = data
                for magic, opener in [
                    (b"\x1f\x8b", gzip.open),
                    (b"BZh", bz2.BZ2File),
                    (b"\xfd7zXZ", lzma.LZMAFile),
                ]:
                    if data.startswith(magic):
                        with opener(io.BytesIO(data)) as stream:
                            decoded = stream.read(MAX_EXPANDED + 1)
                        if len(decoded) > MAX_EXPANDED:
                            raise ValueError("El contenido supera los 20 MB.")
                        break
                try:
                    archive = tarfile.open(fileobj=io.BytesIO(decoded), mode="r:")
                except tarfile.ReadError:
                    if decoded is data:
                        raise ValueError(
                            "Formato no soportado: usa ZIP, 7z, TAR, gzip, bzip2 o xz."
                        ) from None
                    name = re.sub(r"(?i)\.(gz|gzip|bz2|xz)$", "", filename)
                    if Path(name).suffix.lower() not in EXTENSIONS:
                        raise ValueError(
                            "La fuente comprimida debe conservar su extensión Fortran."
                        ) from None
                    add(name, decoded)
                else:
                    with archive:
                        for member in archive:
                            while member.name.startswith("./"):
                                member.name = member.name[2:]
                            if member.isdir() and member.name in {"", "."}:
                                continue
                            if not (member.isdir() or member.isfile()):
                                raise ValueError(
                                    "El archivo contiene enlaces o archivos especiales."
                                )
                            if member.size + expanded > MAX_EXPANDED:
                                raise ValueError("El contenido supera los 20 MB.")
                            if member.isdir():
                                add(member.name.rstrip("/") + "/", b"")
                            else:
                                with archive.extractfile(member) as stream:
                                    add(member.name, stream.read(MAX_EXPANDED - expanded + 1))
        # The original compressed upload was bounded; normalization may be larger.
        return _extract_zip(output.getvalue(), destination)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Archivo comprimido inválido, dañado o con un método no soportado."
        ) from exc


def _extraction_worker(connection, data, destination, filename):
    try:
        connection.send((True, extract_sources(data, destination, filename)))
    except Exception as exc:
        connection.send((False, str(exc)))
    finally:
        connection.close()


def bounded_extract(data, destination, filename):
    """Terminate decompression after 20 seconds, including malformed native codecs."""
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_extraction_worker, args=(send, data, destination, filename))
    try:
        process.start()
        send.close()
        if not receive.poll(20):
            raise ValueError("Descompresión interrumpida: límite de 20 segundos.")
        try:
            success, result = receive.recv()
        except EOFError:
            raise ValueError("La descompresión terminó sin resultado.") from None
        if not success:
            raise ValueError(result)
        return result
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate()
                process.join()
