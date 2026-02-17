"""Telegram command handlers and validation helpers."""
from __future__ import annotations

import ipaddress
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable

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


def environment_paths() -> dict[str, Path]:
    root = Path(os.getenv("RECON_ROOT", Path(__file__).resolve().parents[1]))
    return {
        "root": root,
        "scope": root / "config" / "scope.txt",
        "config": root / "config",
        "db": root / "storage" / "history.sqlite",
    }
