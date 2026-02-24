"""Sequential worker that consumes jobs from SQLite queue."""
from __future__ import annotations

import asyncio
import logging

import time
from pathlib import Path

from bot.commands import environment_paths, init_db
from recon_settings import load_settings
=======

from bot.notifier import notify_job_update
from runner.scheduler import JobQueue, initialize_summary, load_summary, make_run_dir, run_modules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("recon-worker")


async def process_once(queue: JobQueue, root: Path, token: str | None) -> bool:
    job = queue.next_pending()
    if not job:
        return False

    logger.info("Processing job=%s domain=%s profile=%s", job.id, job.domain, job.profile)
    run_dir = make_run_dir(root, job.domain, job.id)
    summary_path = run_dir / "summary.json"
    initialize_summary(summary_path, job.domain, job.profile, job.id)

    status = "completed"
    error = None
    try:
        run_modules(root, job.domain, job.profile, run_dir, summary_path)
    except Exception as exc:  # broad to keep worker alive
        status = "failed"
        error = str(exc)
        logger.exception("Job %s failed", job.id)

    summary = load_summary(summary_path)
    queue.finish(job.id, status, str(run_dir), summary, error)

    if token:
        await notify_job_update(
            token=token,
            chat_id=job.chat_id,
            job_id=job.id,
            domain=job.domain,
            status=status,
            run_dir=str(run_dir),
            summary=summary,
        )
    return True


def main() -> None:
    settings = load_settings()
    root = settings.recon_root
    paths = environment_paths()
    init_db(paths["db"])
    queue = JobQueue(paths["db"])
    token = settings.telegram_bot_token

    poll_seconds = settings.worker_poll_seconds


    logger.info("Recon worker started with poll=%ss", poll_seconds)

    while True:
        processed = asyncio.run(process_once(queue, root, token))
        if not processed:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
