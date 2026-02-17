"""Queue and pipeline utilities for recon jobs."""
from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Job:
    id: int
    domain: str
    profile: str
    chat_id: int
    requested_by: str | None


class JobQueue:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def next_pending(self) -> Job | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, domain, profile, chat_id, requested_by
                FROM jobs WHERE status='pending'
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE jobs SET status='running', started_at=CURRENT_TIMESTAMP WHERE id=?",
                (row[0],),
            )
            conn.commit()
            return Job(*row)

    def finish(
        self,
        job_id: int,
        status: str,
        run_dir: str,
        summary_json: str,
        error: str | None = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status=?, finished_at=CURRENT_TIMESTAMP, run_dir=?, summary=?, error=?
                WHERE id=?
                """,
                (status, run_dir, summary_json, error, job_id),
            )
            conn.commit()


def make_run_dir(root: Path, domain: str, job_id: int) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = root / "storage" / "recon" / f"{domain}_{ts}_job{job_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def initialize_summary(summary_path: Path, domain: str, profile: str, job_id: int) -> None:
    payload = {
        "job_id": job_id,
        "domain": domain,
        "profile": profile,
        "started_at": datetime.utcnow().isoformat(),
        "modules": {},
        "highlights": {},
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_modules(root: Path, domain: str, profile: str, run_dir: Path, summary_path: Path) -> None:
    modules = sorted((root / "modules").glob("*.sh"))
    profile_file = root / "config" / "profiles" / f"{profile}.yml"
    tools_file = root / "config" / "tools.yml"

    for script in modules:
        cmd = [
            "bash",
            str(script),
            domain,
            str(run_dir),
            str(summary_path),
            str(profile_file),
            str(tools_file),
        ]
        subprocess.run(cmd, check=True)


def load_summary(summary_path: Path) -> str:
    return summary_path.read_text(encoding="utf-8")
