"""Bounded streaming extraction. Uploaded archives and decoder output stay on disk."""

import io
import re
import stat
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .project import EXCLUDED_DIRS, EXTENSIONS

MAX_UPLOAD = 4 * 1024**3
MAX_EXPANDED = 8 * 1024**3
MAX_SOURCE = 2_000_000
MAX_TOTAL_SOURCES = 20_000_000
MAX_SOURCES = 100
EXTRACTION_TIMEOUT = 1800
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def _parts(name, seen):
    raw = name.rstrip("/")
    parts = raw.split("/")
    if (
        not raw
        or len(raw) > 240
        or "\\" in raw
        or any(ord(c) < 32 for c in raw)
        or any(
            p in {"", ".", ".."} or ":" in p or p.endswith((".", " ")) or _RESERVED.match(p)
            for p in parts
        )
        or PurePosixPath(raw).is_absolute()
    ):
        raise ValueError("El ZIP contiene una ruta no permitida.")
    key = raw.casefold()
    if key in seen:
        raise ValueError("El ZIP contiene rutas duplicadas o ambiguas.")
    seen.add(key)
    return parts


class _Collector:
    def __init__(self, destination):
        self.destination = destination
        self.seen = set()
        self.expanded = self.sources = self.source_bytes = 0

    def member(self, name, size, directory=False):
        parts = _parts(name, self.seen)
        self.expanded += size
        if self.expanded > MAX_EXPANDED:
            raise ValueError("El contenido supera los 8 GiB descomprimidos.")
        if directory or any(p in EXCLUDED_DIRS for p in parts[:-1]):
            return None
        if PurePosixPath(name).suffix.lower() not in EXTENSIONS:
            return None
        if size > MAX_SOURCE:
            raise ValueError("Una fuente Fortran supera los 2 MB.")
        self.sources += 1
        self.source_bytes += size
        if self.sources > MAX_SOURCES:
            raise ValueError("El archivo supera los 100 archivos Fortran.")
        if self.source_bytes > MAX_TOTAL_SOURCES:
            raise ValueError("Las fuentes Fortran superan los 20 MB en total.")
        target = self.destination.joinpath(*parts)
        if not target.resolve().is_relative_to(self.destination.resolve()):
            raise ValueError("Ruta fuera del directorio de trabajo.")
        return target

    def write(self, target, stream):
        if target is None:
            return
        content = stream.read(MAX_SOURCE + 1)
        if len(content) > MAX_SOURCE:
            raise ValueError("Una fuente Fortran supera los 2 MB.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(content)


@contextmanager
def _input(data):
    with io.BytesIO(data) if isinstance(data, bytes) else Path(data).open("rb") as stream:
        stream.seek(0, 2)
        if stream.tell() > MAX_UPLOAD:
            raise ValueError("El archivo comprimido supera los 4 GiB.")
        stream.seek(0)
        yield stream


def extract_sources(data: bytes | Path, destination: Path, filename="source.f90.gz") -> int:
    import bz2
    import gzip
    import lzma
    import tarfile

    import py7zr

    collector = _Collector(destination)
    try:
        with _input(data) as stream:
            if zipfile.is_zipfile(stream):
                with zipfile.ZipFile(stream) as archive:
                    for entry in archive.infolist():
                        mode = (entry.external_attr >> 16) & 0xFFFF
                        if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                            raise ValueError("El ZIP contiene enlaces o archivos especiales.")
                        if entry.flag_bits & 1:
                            raise ValueError("No se admiten archivos cifrados.")
                        target = collector.member(
                            entry.orig_filename, entry.file_size, entry.is_dir()
                        )
                        if target:
                            with archive.open(entry) as source:
                                collector.write(target, source)
            else:
                stream.seek(0)
                if py7zr.is_7zfile(stream):
                    _seven_zip(stream, collector)
                else:
                    stream.seek(0)
                    magic = stream.read(6)
                    stream.seek(0)
                    opener = next(
                        (
                            op
                            for signature, op in [
                                (b"\x1f\x8b", gzip.open),
                                (b"BZh", bz2.BZ2File),
                                (b"\xfd7zXZ", lzma.LZMAFile),
                            ]
                            if magic.startswith(signature)
                        ),
                        None,
                    )
                    # A seekable disk spool allows TAR detection without retaining expanded data.
                    with tempfile.TemporaryFile(dir=destination.parent) as decoded:
                        if opener:
                            with opener(stream) as compressed:
                                total = 0
                                while chunk := compressed.read(1024 * 1024):
                                    total += len(chunk)
                                    if total > MAX_EXPANDED:
                                        raise ValueError(
                                            "El contenido supera los 8 GiB descomprimidos."
                                        )
                                    decoded.write(chunk)
                            decoded.seek(0)
                            source = decoded
                        else:
                            source = stream
                        try:
                            archive = tarfile.open(fileobj=source, mode="r:")
                        except tarfile.ReadError:
                            if not opener:
                                raise ValueError(
                                    "Formato no soportado: usa ZIP, 7z, TAR, gzip, bzip2 o xz."
                                ) from None
                            source.seek(0, 2)
                            size = source.tell()
                            source.seek(0)
                            name = re.sub(r"(?i)\.(gz|gzip|bz2|xz)$", "", filename)
                            target = collector.member(name, size)
                            collector.write(target, source)
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
                                    target = collector.member(
                                        member.name, member.size, member.isdir()
                                    )
                                    if target:
                                        with archive.extractfile(member) as item:
                                            collector.write(target, item)
        if not collector.sources:
            raise ValueError("El archivo no contiene fuentes Fortran compatibles.")
        return collector.sources
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Archivo comprimido inválido, dañado o con método no soportado.") from exc


def _seven_zip(stream, collector):
    import py7zr
    from py7zr.io import WriterFactory

    stream.seek(0)
    with py7zr.SevenZipFile(stream) as archive:
        if archive.needs_password():
            raise ValueError("No se admiten archivos cifrados.")
        targets = {}
        for member in archive.files:
            if member.is_symlink or member.is_junction or member.is_socket:
                raise ValueError("El archivo contiene enlaces o archivos especiales.")
            targets[member.filename] = collector.member(
                member.filename, member.uncompressed, member.is_directory
            )
        actual = 0

        class Sink(io.BytesIO):
            def __init__(self, target):
                super().__init__()
                self.target = target
                self.count = 0

            def write(self, chunk):
                nonlocal actual
                actual += len(chunk)
                self.count += len(chunk)
                if actual > MAX_EXPANDED:
                    raise ValueError("El contenido supera los 8 GiB descomprimidos.")
                if self.target:
                    if self.count > MAX_SOURCE:
                        raise ValueError("Una fuente Fortran supera los 2 MB.")
                    return super().write(chunk)
                return len(chunk)  # Consume unneeded solid-block members without retaining them.

            def close(self):
                pass

            def size(self):
                return self.count

        class Factory(WriterFactory):
            def __init__(self):
                self.streams = []

            def create(self, name):
                sink = Sink(targets[name])
                self.streams.append(sink)
                return sink

        factory = Factory()
        archive.extractall(factory=factory)
        for sink in factory.streams:
            if sink.target:
                sink.seek(0)
                collector.write(sink.target, sink)


def _extraction_worker(connection, data, destination, filename):
    try:
        connection.send((True, extract_sources(data, destination, filename)))
    except Exception as exc:
        connection.send((False, str(exc)))
    finally:
        connection.close()


def bounded_extract(data, destination, filename):
    """Terminate decompression after 30 minutes, including malformed native codecs."""
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_extraction_worker, args=(send, data, destination, filename))
    try:
        process.start()
        send.close()
        if not receive.poll(EXTRACTION_TIMEOUT):
            raise ValueError("Descompresión interrumpida: límite de 30 minutos.")
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
