"""Centralized runtime settings loader for bot/worker.

Priority order:
1) YAML file (RECON_CONFIG_FILE or config/app.yml)
2) Environment variables fallback
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class AppSettings:
    recon_root: Path
    telegram_bot_token: str | None
    worker_poll_seconds: int
    sqlite_path: Path
    scope_file: Path
    tools_file: Path
    profiles_dir: Path



def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def load_settings() -> AppSettings:
    default_root = Path(__file__).resolve().parent
    recon_root = Path(os.getenv("RECON_ROOT", default_root))

    config_file = Path(os.getenv("RECON_CONFIG_FILE", recon_root / "config" / "app.yml"))
    cfg = _load_yaml(config_file)

    app_cfg = cfg.get("app", {})
    tg_cfg = cfg.get("telegram", {})
    worker_cfg = cfg.get("worker", {})
    paths_cfg = cfg.get("paths", {})

    root = Path(app_cfg.get("recon_root", recon_root))
    token = tg_cfg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
    poll = int(worker_cfg.get("poll_seconds", os.getenv("WORKER_POLL_SECONDS", "15")))

    sqlite_path = Path(paths_cfg.get("sqlite", root / "storage" / "history.sqlite"))
    scope_file = Path(paths_cfg.get("scope", root / "config" / "scope.txt"))
    tools_file = Path(paths_cfg.get("tools", root / "config" / "tools.yml"))
    profiles_dir = Path(paths_cfg.get("profiles", root / "config" / "profiles"))

    return AppSettings(
        recon_root=root,
        telegram_bot_token=token,
        worker_poll_seconds=poll,
        sqlite_path=sqlite_path,
        scope_file=scope_file,
        tools_file=tools_file,
        profiles_dir=profiles_dir,
    )
