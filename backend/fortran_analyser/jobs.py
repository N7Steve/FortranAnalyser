"""Bounded single-worker queue with optional atomic on-disk result records."""

import json
import logging
import os
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .archive import extract_sources
from .project import analyse_project

logger = logging.getLogger(__name__)
TERMINAL = {"completed", "failed", "cancelled"}


@dataclass
class Job:
    id: str
    name: str
    source_form: str
    status: str = "uploading"
    processed: int = 0
    total: int = 0
    error: str | None = None
    report: dict | None = None
    cancel: threading.Event = field(default_factory=threading.Event)

    def snapshot(self):
        return {
            key: getattr(self, key)
            for key in (
                "id",
                "name",
                "source_form",
                "status",
                "processed",
                "total",
                "error",
            )
        }


class JobStore:
    def __init__(self, root: Path, *, persistent: bool = False):
        self.root = root
        self.persistent = persistent
        self.lock = threading.RLock()
        self.jobs: dict[str, Job] = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")
        if persistent:
            self._restore()

    def _save(self, job: Job):
        if not self.persistent:
            return
        directory = self.root / job.id
        directory.mkdir(exist_ok=True)
        temporary = directory / ".analysis.json.tmp"
        temporary.write_text(
            json.dumps(
                {
                    "storage_version": 1,
                    "job": job.snapshot(),
                    "report": job.report,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, directory / ".analysis.json")

    def _restore(self):
        """Restore only our versioned records; leave unrelated/corrupt files untouched."""
        for directory in sorted(self.root.iterdir()):
            if (
                directory.is_symlink()
                or not directory.is_dir()
                or not re.fullmatch(r"[0-9a-f]{32}", directory.name)
            ):
                continue
            state = directory / ".analysis.json"
            if not state.is_file() or state.is_symlink():
                continue
            try:
                if state.stat().st_size > 32_000_000:
                    raise ValueError("Stored record exceeds size limit")
                payload = json.loads(state.read_text(encoding="utf-8"))
                saved = payload["job"]
                if payload["storage_version"] != 1 or saved["id"] != directory.name:
                    raise ValueError("Unrecognized stored record")
                if saved["source_form"] not in {"auto", "free", "fixed"}:
                    raise ValueError("Unrecognized source format")
                if saved["status"] not in TERMINAL | {
                    "uploading",
                    "queued",
                    "extracting",
                    "running",
                }:
                    raise ValueError("Unrecognized job status")
                job = Job(
                    id=saved["id"],
                    name=saved["name"],
                    source_form=saved["source_form"],
                    status=saved["status"],
                    processed=saved["processed"],
                    total=saved["total"],
                    error=saved["error"],
                    report=payload["report"],
                )
                if job.status == "completed":
                    if not isinstance(job.report, dict) or job.report.get("schema_version") != "1":
                        raise ValueError("Missing or incompatible stored report")
                    if not isinstance(job.report.get("files"), list):
                        raise ValueError("Invalid stored file list")
                elif job.status not in TERMINAL:
                    # A saved, owned record proves this was our interrupted work.
                    # Discard incomplete sources and explain the interruption; do not rerun them.
                    job.status = "failed"
                    job.error = "Análisis interrumpido por un reinicio. Vuelve a subir el ZIP."
                    job.report = None
                    shutil.rmtree(directory)
                    self._save(job)
                if len(self.jobs) < 8:
                    self.jobs[job.id] = job
                else:
                    logger.warning("Stored analysis %s exceeds the session capacity", job.id)
            except (OSError, ValueError, KeyError, TypeError):
                logger.warning(
                    "Ignoring unreadable analysis record %s", directory.name, exc_info=True
                )

    def create(self, name: str, source_form: str) -> Job:
        with self.lock:
            if (
                len(self.jobs) >= 8
                or sum(j.status not in TERMINAL for j in self.jobs.values()) >= 3
            ):
                raise ValueError("Cola llena. Espera o elimina un análisis anterior.")
            job = Job(uuid.uuid4().hex, name, source_form)
            self.jobs[job.id] = job
            return job

    def get(self, identifier: str) -> Job:
        with self.lock:
            return self.jobs[identifier]

    def submit(self, job: Job, data: bytes):
        with self.lock:
            job.status = "queued"
            self._save(job)
        self.executor.submit(self._run, job, data)

    def _run(self, job: Job, data: bytes):
        directory = self.root / job.id
        try:
            if job.cancel.is_set():
                return
            with self.lock:
                job.status = "extracting"
            directory.mkdir(exist_ok=True)
            total = extract_sources(data, directory)
            with self.lock:
                job.total = total
                job.status = "running"

            def progress(processed, total):
                with self.lock:
                    job.processed, job.total = processed, total

            report = analyse_project(
                directory,
                source_form=job.source_form,
                max_files=100,
                timeout=5,
                on_progress=progress,
                should_cancel=job.cancel.is_set,
            )
            with self.lock:
                if not job.cancel.is_set():
                    job.report = report.to_dict()
                    job.status = "completed"
                    self._save(job)
        except ValueError as exc:
            with self.lock:
                job.status, job.error = "failed", str(exc)
        except Exception:
            logger.exception("Analysis job %s failed", job.id)
            with self.lock:
                job.status, job.error = "failed", "Error interno al procesar el proyecto."
        finally:
            with self.lock:
                if job.cancel.is_set():
                    job.status = "cancelled"
                if job.status != "completed":
                    shutil.rmtree(directory, ignore_errors=True)
                    try:
                        self._save(job)
                    except OSError:
                        logger.exception("Cannot save failed/cancelled analysis %s", job.id)

    def delete(self, identifier: str):
        with self.lock:
            job = self.jobs[identifier]
            if job.status not in TERMINAL:
                job.cancel.set()
                return False
            shutil.rmtree(self.root / job.id, ignore_errors=True)
            del self.jobs[identifier]
            return True

    def close(self):
        with self.lock:
            for job in self.jobs.values():
                job.cancel.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
