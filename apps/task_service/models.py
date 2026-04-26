from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


JOB_STATUSES = ("queued", "running", "success", "failed", "cancelled")


@dataclass
class Job:
    job_id: str
    created_at: str
    updated_at: str
    status: str
    task_type: str
    params_json: str
    stages_json: str
    current_stage: str
    progress: float
    log_path: str
    artifact_index_path: str
    error_message: str
    started_at: str
    finished_at: str
    exit_code: int | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Job":
        return cls(
            job_id=row["job_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=row["status"],
            task_type=row["task_type"],
            params_json=row["params_json"],
            stages_json=row["stages_json"],
            current_stage=row["current_stage"] or "",
            progress=float(row["progress"] or 0.0),
            log_path=row["log_path"] or "",
            artifact_index_path=row["artifact_index_path"] or "",
            error_message=row["error_message"] or "",
            started_at=row["started_at"] or "",
            finished_at=row["finished_at"] or "",
            exit_code=row["exit_code"],
        )


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
