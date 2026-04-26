from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .queue import JobQueue
from .worker import JobWorker


DEFAULT_STAGES = ["generate", "blank", "simulate", "render", "snr", "build", "train"]


class TaskService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        runtime = project_root / "artifacts" / "streamlit_runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        self.queue = JobQueue(runtime / "jobs.sqlite3")
        self.worker = JobWorker(self.queue, project_root=project_root)
        self.worker.start()

    def submit_pipeline_job(self, params: dict[str, Any], stages: list[str] | None = None) -> str:
        chosen_stages = stages or list(DEFAULT_STAGES)
        job_id = self.queue.enqueue(
            task_type="pipeline",
            params=params,
            stages=chosen_stages,
            log_path=self.project_root / "artifacts" / "logs" / "pending.log",
            artifact_index=self.project_root / "artifacts" / "job_artifacts" / "pending.json",
        )
        job = self.queue.get_job(job_id)
        if job:
            # Ensure deterministic per-job paths after ID creation.
            log_path = self.project_root / "artifacts" / "logs" / f"{job_id}.log"
            artifact_path = self.project_root / "artifacts" / "job_artifacts" / f"{job_id}.json"
            self.queue.update_job(job_id, log_path=str(log_path), artifact_index_path=str(artifact_path))
            snapshot_dir = self.project_root / "artifacts" / "job_params"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            (snapshot_dir / f"{job_id}.json").write_text(json.dumps({"params": params, "stages": chosen_stages}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return job_id

    def list_jobs(self, limit: int = 50):
        return self.queue.list_jobs(limit=limit)

    def get_job(self, job_id: str):
        return self.queue.get_job(job_id)

    def cancel_job(self, job_id: str) -> bool:
        return self.queue.cancel_job(job_id)

    def read_log_tail(self, job_id: str, max_chars: int = 8000) -> str:
        job = self.get_job(job_id)
        if job is None or not job.log_path:
            return ""
        path = Path(job.log_path)
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
