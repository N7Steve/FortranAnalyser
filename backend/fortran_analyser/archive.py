"""Streaming extraction without size quotas. Files stay in a server-owned directory."""

import io
import re
import shutil
import stat
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .project import EXCLUDED_DIRS, EXTENSIONS

_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def _parts(name, seen, *, portable=True):
    raw = name.rstrip("/")
    parts = raw.split("/")
    if (
        not raw
        or "\\" in raw
        or any(ord(c) < 32 for c in raw)
        or any(
            p in {"", ".", ".."}
            or (portable and (":" in p or p.endswith((".", " ")) or _RESERVED.match(p)))
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
        is_source = not directory and PurePosixPath(name).suffix.lower() in EXTENSIONS
        # Portability restrictions apply only to names actually written to disk.
        # Structural traversal/absolute/duplicate checks still cover every member.
        parts = _parts(name, self.seen, portable=is_source)
        self.expanded += size
        if directory or any(p in EXCLUDED_DIRS for p in parts[:-1]):
            return None
        if PurePosixPath(name).suffix.lower() not in EXTENSIONS:
            return None
        self.sources += 1
        self.source_bytes += size
        target = self.destination.joinpath(*parts)
        if not target.resolve().is_relative_to(self.destination.resolve()):
            raise ValueError("Ruta fuera del directorio de trabajo.")
        return target

    def write(self, target, stream):
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            shutil.copyfileobj(stream, output, length=1024 * 1024)


@contextmanager
def _input(data):
    with io.BytesIO(data) if isinstance(data, bytes) else Path(data).open("rb") as stream:
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
                                shutil.copyfileobj(compressed, decoded, length=1024 * 1024)
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

        class Sink:
            def __init__(self, target):
                self.target = target
                self.count = 0
                self.stream = (
                    tempfile.TemporaryFile(dir=collector.destination.parent) if target else None
                )

            def write(self, chunk):
                self.count += len(chunk)
                return self.stream.write(chunk) if self.stream else len(chunk)

            def read(self, size=-1):
                return self.stream.read(size) if self.stream else b""

            def seek(self, offset, whence=0):
                return self.stream.seek(offset, whence) if self.stream else 0

            def flush(self):
                if self.stream:
                    self.stream.flush()

            def close(self):
                pass  # py7zr closes its writers before we collect them.

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
        try:
            archive.extractall(factory=factory)
            for sink in factory.streams:
                if sink.target:
                    sink.seek(0)
                    collector.write(sink.target, sink)
        finally:
            for sink in factory.streams:
                if sink.stream:
                    sink.stream.close()


def _extraction_worker(connection, data, destination, filename):
    try:
        connection.send((True, extract_sources(data, destination, filename)))
    except Exception as exc:
        connection.send((False, str(exc)))
    finally:
        connection.close()


def bounded_extract(data, destination, filename, should_cancel=None):
    """Isolate extraction; wait without a deadline, allowing explicit cancellation."""
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_extraction_worker, args=(send, data, destination, filename))
    try:
        if should_cancel and should_cancel():
            raise ValueError("Descompresión cancelada.")
        process.start()
        send.close()
        while not receive.poll(0.2):
            if should_cancel and should_cancel():
                raise ValueError("Descompresión cancelada.")
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
