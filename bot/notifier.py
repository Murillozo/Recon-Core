"""Helpers to send notifications back to Telegram users/chats."""
from __future__ import annotations

import json
from pathlib import Path

from telegram import Bot


def build_completion_message(job_id: int, domain: str, status: str, run_dir: str, summary: str) -> str:
    base = [
        "✅ *Recon finalizado*" if status == "completed" else "❌ *Recon falhou*",
        f"Job: `{job_id}`",
        f"Domínio: `{domain}`",
        f"Status: `{status}`",
        f"Relatório: `{Path(run_dir) / 'report.md'}`",
    ]
    if summary:
        try:
            data = json.loads(summary)
            highlights = data.get("highlights", {})
            base.append(
                "Resumo: "
                + ", ".join(f"{k}={v}" for k, v in highlights.items())
            )
        except json.JSONDecodeError:
            pass
    return "\n".join(base)


async def notify_job_update(
    token: str,
    chat_id: int,
    job_id: int,
    domain: str,
    status: str,
    run_dir: str,
    summary: str,
) -> None:
    bot = Bot(token=token)
    text = build_completion_message(job_id, domain, status, run_dir, summary)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
