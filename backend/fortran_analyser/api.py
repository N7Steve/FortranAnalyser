"""Personal web API. Optional on-disk results; run with one worker."""

import asyncio
import io
import os
import tempfile
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
        allow_methods=["GET", "POST", "DELETE"],
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
        return {"persistent": store(request).persistent}

    @app.get("/api/analyses")
    def analyses(request: Request):
        with store(request).lock:
            return [job.snapshot() for job in store(request).jobs.values()]

    @app.get("/api/example")
    def example():
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(Path(__file__).with_name("example").iterdir()):
                archive.write(path, f"example/{path.name}")
        return Response(buffer.getvalue(), media_type="application/zip")

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
        }:
            raise HTTPException(415, "Envía un archivo ZIP como cuerpo de la petición.")
        try:
            job = store(request).create(name, source_form)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc
        try:
            data = bytearray()
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    if len(data) + len(chunk) > MAX_UPLOAD:
                        raise HTTPException(413, "El ZIP supera los 10 MB.")
                    data.extend(chunk)
            await run_in_threadpool(store(request).submit, job, bytes(data))
            with store(request).lock:
                return job.snapshot()
        except BaseException as exc:
            with store(request).lock:
                store(request).jobs.pop(job.id, None)
            if isinstance(exc, TimeoutError):
                raise HTTPException(408, "Tiempo de carga agotado.") from exc
            raise

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
