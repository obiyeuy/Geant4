from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import JOB_STATUSES, Job, now_iso


class JobQueue:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    stages_json TEXT NOT NULL,
                    current_stage TEXT,
                    progress REAL DEFAULT 0.0,
                    log_path TEXT,
                    artifact_index_path TEXT,
                    error_message TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    exit_code INTEGER
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )

    def _next_job_id(self) -> str:
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO counters(name, value) VALUES('job_seq', 0)")
            row = conn.execute("SELECT value FROM counters WHERE name='job_seq'").fetchone()
            current = int(row["value"]) if row else 0
            nxt = current + 1
            conn.execute("UPDATE counters SET value=? WHERE name='job_seq'", (nxt,))
        return f"J{nxt:06d}"

    def enqueue(self, task_type: str, params: dict[str, Any], stages: list[str], log_path: Path, artifact_index: Path) -> str:
        job_id = self._next_job_id()
        t = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs(
                    job_id, created_at, updated_at, status, task_type,
                    params_json, stages_json, current_stage, progress,
                    log_path, artifact_index_path, error_message, started_at, finished_at, exit_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    t,
                    t,
                    "queued",
                    task_type,
                    json.dumps(params, ensure_ascii=False),
                    json.dumps(stages, ensure_ascii=False),
                    "",
                    0.0,
                    str(log_path),
                    str(artifact_index),
                    "",
                    "",
                    "",
                    None,
                ),
            )
        return job_id

    def claim_next(self) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            t = now_iso()
            conn.execute(
                """
                UPDATE jobs
                SET status='running', started_at=?, updated_at=?
                WHERE job_id=? AND status='queued'
                """,
                (t, t, row["job_id"]),
            )
            confirmed = conn.execute("SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)).fetchone()
            if confirmed is None or confirmed["status"] != "running":
                return None
            return Job.from_row(dict(confirmed))

    def update_job(self, job_id: str, **updates: Any) -> None:
        if not updates:
            return
        if "status" in updates and updates["status"] not in JOB_STATUSES:
            raise ValueError(f"Unsupported status: {updates['status']}")
        updates["updated_at"] = now_iso()
        columns = ", ".join(f"{k}=?" for k in updates.keys())
        values = list(updates.values())
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {columns} WHERE job_id=?", values)

    def get_job(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            return Job.from_row(dict(row)) if row else None

    def list_jobs(self, limit: int = 50) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [Job.from_row(dict(r)) for r in rows]

    def cancel_job(self, job_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                return False
            if row["status"] in ("success", "failed", "cancelled"):
                return False
            conn.execute(
                "UPDATE jobs SET status='cancelled', updated_at=?, finished_at=? WHERE job_id=?",
                (now_iso(), now_iso(), job_id),
            )
        return True
