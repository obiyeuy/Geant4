from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .queue import JobQueue
from .runner import run_pipeline_job


class JobWorker:
    def __init__(self, queue: JobQueue, project_root: Path, poll_interval: float = 1.5) -> None:
        self.queue = queue
        self.project_root = project_root
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            job = self.queue.claim_next()
            if job is None:
                time.sleep(self.poll_interval)
                continue
            self._execute_job(job.job_id)

    def _execute_job(self, job_id: str) -> None:
        job = self.queue.get_job(job_id)
        if job is None or job.status != "running":
            return
        try:
            params = json.loads(job.params_json)
            stages = json.loads(job.stages_json)
            log_path = Path(job.log_path)
            artifact_index = Path(job.artifact_index_path)

            def on_stage_update(stage: str, progress: float) -> None:
                self.queue.update_job(job_id, current_stage=stage, progress=progress)

            result = run_pipeline_job(
                project_root=self.project_root,
                params=params,
                stages=stages,
                log_path=log_path,
                artifact_index_path=artifact_index,
                on_stage_update=on_stage_update,
            )
            status = "success" if result.exit_code == 0 else "failed"
            self.queue.update_job(
                job_id,
                status=status,
                current_stage=result.stage or "completed",
                progress=1.0 if status == "success" else job.progress,
                error_message=result.error_message,
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                exit_code=result.exit_code,
            )
        except Exception as exc:
            self.queue.update_job(
                job_id,
                status="failed",
                error_message=str(exc),
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                exit_code=-1,
            )
