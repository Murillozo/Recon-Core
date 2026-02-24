import sqlite3
from pathlib import Path

from bot.commands import enqueue_job, init_db
from runner.scheduler import JobQueue


def test_job_queue_lifecycle(tmp_path: Path):
    db = tmp_path / "history.sqlite"
    init_db(db)
    job_id = enqueue_job(db, "example.com", "balanced", 1, "tester")
    queue = JobQueue(db)
    job = queue.next_pending()
    assert job is not None
    assert job.id == job_id
    queue.finish(job_id, "completed", "/tmp/run", "{}")

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT status, run_dir FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert row == ("completed", "/tmp/run")
