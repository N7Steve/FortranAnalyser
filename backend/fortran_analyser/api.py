"""Personal web API. Optional on-disk results; run with one worker."""

import asyncio
import io
import os
import tempfile
import time
import zipfile
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .archive import MAX_UPLOAD
from .jobs import JobStore


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        with ExitStack() as stack:
            data_dir = os.environ.get("FORTRAN_DATA_DIR")
            if data_dir:
                directory = Path(data_dir).expanduser().resolve() / "analyses"
                directory.mkdir(parents=True, exist_ok=True)
            else:
                directory = Path(
                    stack.enter_context(tempfile.TemporaryDirectory(prefix="fortran-web-"))
                )
            # Fail at startup, rather than accepting uploads into unwritable storage.
            with tempfile.TemporaryFile(dir=directory) as probe:
                probe.write(b"ready")
            store = JobStore(directory, persistent=bool(data_dir))
            app.state.store = store
            try:
                yield
            finally:
                await run_in_threadpool(store.close)

    app = FastAPI(title="FortranAnalyser", version="0.2.0", lifespan=lifespan)
    extra_hosts = [
        h.strip() for h in os.environ.get("FORTRAN_ALLOWED_HOSTS", "").split(",") if h.strip()
    ]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver", *extra_hosts],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def store(request: Request) -> JobStore:
        return request.app.state.store

    def job_for(request, identifier):
        try:
            return store(request).get(identifier)
        except KeyError:
            raise HTTPException(404, "Análisis no encontrado en esta sesión.") from None

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/config")
    def configuration(request: Request):
        return {
            "persistent": store(request).persistent,
            "max_upload_bytes": MAX_UPLOAD,
            "upload_chunk_bytes": 8 * 1024**2,
        }

    @app.get("/api/analyses")
    def analyses(request: Request):
        with store(request).lock:
            store(request).expire_uploads()
            return [job.snapshot() for job in store(request).jobs.values()]

    @app.get("/api/example")
    def example():
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(Path(__file__).with_name("example").iterdir()):
                archive.write(path, f"example/{path.name}")
        return Response(buffer.getvalue(), media_type="application/zip")

    @app.post("/api/uploads", status_code=201)
    def start_upload(
        request: Request,
        name: str = Query(default="Proyecto", min_length=1, max_length=120),
        source_form: Literal["auto", "free", "fixed"] = "auto",
    ):
        with store(request).lock:
            try:
                job = store(request).create(name, source_form)
                job.chunked = True
            except ValueError as exc:
                raise HTTPException(429, str(exc)) from exc
            try:
                (store(request).root / f"{job.id}.upload").touch(exist_ok=False)
            except OSError as exc:
                store(request).jobs.pop(job.id, None)
                raise HTTPException(507, "No se pudo reservar espacio para la carga.") from exc
            return job.snapshot()

    @app.put("/api/uploads/{identifier}")
    async def upload_chunk(request: Request, identifier: str, offset: int = Query(ge=0)):
        with store(request).lock:
            job = job_for(request, identifier)
            if job.status != "uploading" or job.cancel.is_set():
                raise HTTPException(409, "La carga ya no admite bloques.")
            job.last_activity = time.monotonic()
        data = bytearray()
        try:
            async with asyncio.timeout(120):
                async for chunk in request.stream():
                    if len(data) + len(chunk) > 8 * 1024**2:
                        raise HTTPException(413, "Cada bloque admite hasta 8 MiB.")
                    data.extend(chunk)
        except TimeoutError as exc:
            raise HTTPException(408, "Tiempo de recepción del bloque agotado.") from exc
        if not data:
            raise HTTPException(400, "Bloque vacío.")

        def append():
            with store(request).lock:
                current = job_for(request, identifier)
                if current.status != "uploading" or current.cancel.is_set():
                    raise HTTPException(409, "La carga ya no admite bloques.")
                path = store(request).root / f"{identifier}.upload"
                if path.stat().st_size != offset:
                    raise HTTPException(409, "Bloque fuera de orden. Vuelve a iniciar la subida.")
                if offset + len(data) > MAX_UPLOAD:
                    raise HTTPException(413, "El archivo supera los 4 GiB.")
                try:
                    with path.open("ab") as output:
                        output.write(data)
                except OSError as exc:
                    # Roll back a partial write so a failed request cannot corrupt the offset.
                    with path.open("r+b") as output:
                        output.truncate(offset)
                    raise HTTPException(
                        507, "No se pudo guardar el bloque. Revisa el disco."
                    ) from exc
                current.last_activity = time.monotonic()
                return {"received": offset + len(data)}

        return await run_in_threadpool(append)

    @app.post("/api/uploads/{identifier}/complete", status_code=202)
    def finish_upload(request: Request, identifier: str, size: int = Query(gt=0, le=MAX_UPLOAD)):
        with store(request).lock:
            job = job_for(request, identifier)
            path = store(request).root / f"{identifier}.upload"
            if job.status != "uploading" or job.cancel.is_set():
                raise HTTPException(409, "La carga ya está finalizada o cancelada.")
            if path.stat().st_size != size:
                raise HTTPException(409, "La carga no tiene el tamaño esperado.")
            store(request).submit(job, path)
            return job.snapshot()

    @app.post("/api/analyses", status_code=202)
    async def upload(
        request: Request,
        name: str = Query(default="Proyecto", min_length=1, max_length=120),
        source_form: Literal["auto", "free", "fixed"] = "auto",
    ):
        if request.headers.get("content-type", "").split(";")[0] not in {
            "application/zip",
            "application/octet-stream",
            "application/x-zip-compressed",
            "application/x-7z-compressed",
            "application/gzip",
            "application/x-tar",
            "application/x-bzip2",
            "application/x-xz",
        }:
            raise HTTPException(415, "Envía un archivo comprimido como cuerpo de la petición.")
        length = request.headers.get("content-length")
        if length and length.isdecimal() and int(length) > MAX_UPLOAD:
            raise HTTPException(413, "El archivo supera los 4 GiB.")
        try:
            job = store(request).create(name, source_form)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc
        upload_path = store(request).root / f"{job.id}.upload"
        submitted = False
        try:
            size = 0
            with upload_path.open("xb") as output:
                chunks = request.stream().__aiter__()
                async with asyncio.timeout(24 * 60 * 60):
                    while True:
                        try:
                            chunk = await asyncio.wait_for(anext(chunks), timeout=120)
                        except StopAsyncIteration:
                            break
                        size += len(chunk)
                        if size > MAX_UPLOAD:
                            raise HTTPException(413, "El archivo supera los 4 GiB.")
                        if job.cancel.is_set():
                            raise HTTPException(409, "Carga cancelada.")
                        await run_in_threadpool(output.write, chunk)
            await run_in_threadpool(store(request).submit, job, upload_path)
            submitted = True
            with store(request).lock:
                return job.snapshot()
        except TimeoutError as exc:
            raise HTTPException(408, "Tiempo de carga agotado (120 s sin recibir datos).") from exc
        except OSError as exc:
            raise HTTPException(
                507, "No se pudo guardar la carga. Comprueba el espacio disponible."
            ) from exc
        finally:
            if not submitted:
                upload_path.unlink(missing_ok=True)
                with store(request).lock:
                    store(request).jobs.pop(job.id, None)

    @app.get("/api/analyses/{identifier}")
    def status(request: Request, identifier: str):
        with store(request).lock:
            return job_for(request, identifier).snapshot()

    @app.delete("/api/analyses/{identifier}")
    def delete(request: Request, identifier: str):
        with store(request).lock:
            job_for(request, identifier)
            removed = store(request).delete(identifier)
            return JSONResponse({"deleted": removed}, status_code=200 if removed else 202)

    def completed(request, identifier):
        job = job_for(request, identifier)
        if job.status != "completed":
            raise HTTPException(409, "El análisis todavía no tiene resultados disponibles.")
        return job

    @app.get("/api/analyses/{identifier}/report")
    def report(request: Request, identifier: str, download: bool = False):
        with store(request).lock:
            job = completed(request, identifier)
            headers = (
                {"Content-Disposition": 'attachment; filename="analysis.json"'} if download else {}
            )
            return JSONResponse(job.report, headers=headers)

    @app.get("/api/analyses/{identifier}/report.pdf")
    def pdf_report(request: Request, identifier: str):
        from .pdf_report import render_report

        with store(request).lock:
            job = completed(request, identifier)
            report_data, name = job.report, job.name
        return Response(
            render_report(report_data, name),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="FortranAnalyser.pdf"'},
        )

    @app.get("/api/analyses/{identifier}/source")
    def source(request: Request, identifier: str, path: str):
        with store(request).lock:
            job = completed(request, identifier)
            if path not in {file["path"] for file in job.report["files"]}:
                raise HTTPException(404, "Fuente no encontrada en el análisis.")
            base = store(request).root / job.id
            target = base / path
            if target.is_symlink() or not target.resolve().is_relative_to(base.resolve()):
                raise HTTPException(404, "Fuente no encontrada en el análisis.")
            try:
                return {"path": path, "content": target.read_text(encoding="utf-8-sig")}
            except (OSError, UnicodeError) as exc:
                raise HTTPException(422, "No se puede mostrar esta fuente como UTF-8.") from exc

    frontend = Path(
        os.environ.get(
            "FORTRAN_FRONTEND_DIR",
            str(Path(__file__).resolve().parents[2] / "frontend" / "dist"),
        )
    )
    if (frontend / "index.html").is_file():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
