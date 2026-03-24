from pathlib import Path

from bot.commands import (
    cancel_job,
    delete_job,
    enqueue_job,
    get_job_for_chat,
    init_db,
    is_in_scope,
    list_completed_jobs_for_chat,
    list_recent_jobs_for_chat,
    load_scope,
    validate_domain,
)


def test_validate_domain():
    assert validate_domain("example.com")
    assert not validate_domain("http://example.com")
    assert not validate_domain("127.0.0.1")


def test_scope(tmp_path: Path):
    scope = tmp_path / "scope.txt"
    scope.write_text("example.com\n", encoding="utf-8")
    allowed = load_scope(scope)
    assert is_in_scope("app.example.com", allowed)
    assert not is_in_scope("evil.com", allowed)


def test_cancel_pending_job(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    job_id = enqueue_job(db_path, "example.com", "passive", 1234, "tester")
    canceled, reason = cancel_job(db_path, job_id, 1234)

    assert canceled is True
    assert reason == "canceled"


def test_cancel_job_rejects_non_owner(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    job_id = enqueue_job(db_path, "example.com", "passive", 1234, "tester")
    canceled, reason = cancel_job(db_path, job_id, 9999)

    assert canceled is False
    assert reason == "forbidden"


def test_get_job_for_chat(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    job_id = enqueue_job(db_path, "terra.com.br", "passive", 1234, "tester")
    ok, data = get_job_for_chat(db_path, job_id, 1234)

    assert ok is True
    assert data["id"] == str(job_id)
    assert data["domain"] == "terra.com.br"
    assert data["status"] == "pending"


def test_list_recent_jobs_for_chat(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    first = enqueue_job(db_path, "example.com", "passive", 1234, "tester")
    second = enqueue_job(db_path, "terra.com.br", "balanced", 1234, "tester")
    enqueue_job(db_path, "ignored.com", "passive", 9999, "other")

    rows = list_recent_jobs_for_chat(db_path, 1234)

    assert [row["id"] for row in rows] == [str(second), str(first)]
    assert rows[0]["domain"] == "terra.com.br"


def test_delete_job_removes_row_and_run_dir(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    job_id = enqueue_job(db_path, "example.com", "passive", 1234, "tester")
    run_dir = tmp_path / "storage" / "recon" / f"example.com_20260101_000000_job{job_id}"
    run_dir.mkdir(parents=True)
    (run_dir / "proof.txt").write_text("ok", encoding="utf-8")

    deleted, reason, removed_paths = delete_job(db_path, tmp_path, job_id, 1234)

    assert deleted is True
    assert reason == "deleted"
    assert str(run_dir.resolve()) in removed_paths
    assert not run_dir.exists()


def test_list_completed_jobs_for_chat(tmp_path: Path):
    db_path = tmp_path / "history.sqlite"
    init_db(db_path)

    completed = enqueue_job(db_path, "example.com", "passive", 1234, "tester")
    pending = enqueue_job(db_path, "terra.com.br", "balanced", 1234, "tester")

    from sqlite3 import connect

    with connect(db_path) as conn:
        conn.execute(
            "UPDATE jobs SET status='completed', finished_at='2026-01-01 00:00:00', run_dir='/tmp/a' WHERE id=?",
            (completed,),
        )
        conn.execute("UPDATE jobs SET status='pending' WHERE id=?", (pending,))
        conn.commit()

    rows = list_completed_jobs_for_chat(db_path, 1234)
    assert len(rows) == 1
    assert rows[0]["id"] == str(completed)
    assert rows[0]["run_dir"] == "/tmp/a"
