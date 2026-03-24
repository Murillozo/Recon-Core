"""Telegram command handlers and validation helpers."""
from __future__ import annotations

import ipaddress
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Iterable

from recon_settings import load_settings

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$"
)


def validate_domain(domain: str) -> bool:
    """Return True if the provided value looks like a public domain."""
    if not domain:
        return False
    cleaned = domain.strip().lower().rstrip(".")
    if not DOMAIN_RE.match(cleaned):
        return False
    try:
        ipaddress.ip_address(cleaned)
        return False
    except ValueError:
        return True


def load_scope(scope_path: Path) -> set[str]:
    allowed = set()
    if not scope_path.exists():
        return allowed
    for line in scope_path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        allowed.add(line)
    return allowed


def is_in_scope(domain: str, allowed: Iterable[str]) -> bool:
    domain = domain.lower()
    allowed_set = set(allowed)
    if "*" in allowed_set:
        return True
    return any(domain == item or domain.endswith(f".{item}") for item in allowed_set)


def allowed_profiles(base_config: Path) -> set[str]:
    profiles_dir = base_config / "profiles"
    return {p.stem for p in profiles_dir.glob("*.yml")}


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                profile TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                requested_by TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                finished_at TEXT,
                run_dir TEXT,
                summary TEXT,
                error TEXT
            )
            """
        )
        conn.commit()


def enqueue_job(
    db_path: Path,
    domain: str,
    profile: str,
    chat_id: int,
    requested_by: str,
) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO jobs (domain, profile, chat_id, requested_by, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (domain.lower(), profile, chat_id, requested_by),
        )
        conn.commit()
        return int(cursor.lastrowid)


def cancel_job(db_path: Path, job_id: int, chat_id: int) -> tuple[bool, str]:
    """Cancel a pending job that belongs to the provided chat."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, chat_id FROM jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        if not row:
            return False, "not_found"

        status, owner_chat_id = row
        if int(owner_chat_id) != int(chat_id):
            return False, "forbidden"

        if status != "pending":
            return False, status

        conn.execute(
            """
            UPDATE jobs
            SET status='canceled', finished_at=CURRENT_TIMESTAMP, error='Canceled by user'
            WHERE id=?
            """,
            (job_id,),
        )
        conn.commit()
        return True, "canceled"


def delete_job(db_path: Path, recon_root: Path, job_id: int, chat_id: int) -> tuple[bool, str, list[str]]:
    """Delete a job and remove matching artifact directories."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT chat_id, run_dir FROM jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        if not row:
            return False, "not_found", []

        owner_chat_id, run_dir = row
        if int(owner_chat_id) != int(chat_id):
            return False, "forbidden", []

        candidates: list[Path] = []
        if run_dir:
            candidates.append(Path(run_dir))

        recon_dir = recon_root / "storage" / "recon"
        candidates.extend(recon_dir.glob(f"*_job{job_id}"))

        removed_paths: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.resolve())
            if key in seen or not candidate.exists() or not candidate.is_dir():
                continue
            shutil.rmtree(candidate)
            removed_paths.append(key)
            seen.add(key)

        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
        return True, "deleted", removed_paths


def get_job_for_chat(db_path: Path, job_id: int, chat_id: int) -> tuple[bool, dict[str, str] | str]:
    """Return one job status if it belongs to the given chat."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, domain, profile, status, created_at, started_at, finished_at, chat_id
            FROM jobs
            WHERE id=?
            """,
            (job_id,),
        ).fetchone()
        if not row:
            return False, "not_found"

        if int(row[7]) != int(chat_id):
            return False, "forbidden"

        return True, {
            "id": str(row[0]),
            "domain": row[1],
            "profile": row[2],
            "status": row[3],
            "created_at": row[4] or "-",
            "started_at": row[5] or "-",
            "finished_at": row[6] or "-",
        }


def list_recent_jobs_for_chat(db_path: Path, chat_id: int, limit: int = 5) -> list[dict[str, str]]:
    """Return recent jobs for one chat ordered by newest first."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, domain, profile, status, created_at
            FROM jobs
            WHERE chat_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()

    return [
        {
            "id": str(row[0]),
            "domain": row[1],
            "profile": row[2],
            "status": row[3],
            "created_at": row[4] or "-",
        }
        for row in rows
    ]


def list_completed_jobs_for_chat(db_path: Path, chat_id: int, limit: int = 10) -> list[dict[str, str]]:
    """Return completed jobs for one chat ordered by newest first."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, domain, profile, finished_at, run_dir
            FROM jobs
            WHERE chat_id=? AND status='completed'
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()

    return [
        {
            "id": str(row[0]),
            "domain": row[1],
            "profile": row[2],
            "finished_at": row[3] or "-",
            "run_dir": row[4] or "-",
        }
        for row in rows
    ]


def environment_paths() -> dict[str, Path]:
    settings = load_settings()
    return {
        "root": settings.recon_root,
        "db": settings.sqlite_path,
        "scope": settings.scope_file,
        "tools": settings.tools_file,
        "profiles": settings.profiles_dir,
        "config": settings.recon_root / "config",
    }
