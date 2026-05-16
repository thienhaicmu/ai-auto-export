"""
Job manager — tracks active jobs in memory.
Stateless: no DB. Jobs are lost on sidecar restart (by design).
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)

_jobs: dict[str, dict] = {}


def register_job(job_id: str, keyword: str) -> None:
    _jobs[job_id] = {"job_id": job_id, "keyword": keyword, "status": "running"}
    log.info("Job registered: %s", job_id)


def complete_job(job_id: str, outputs: list[str]) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["outputs"] = outputs


def fail_job(job_id: str, error: str) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = error


def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


def list_jobs() -> list[dict]:
    return list(_jobs.values())
