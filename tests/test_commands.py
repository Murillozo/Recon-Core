from pathlib import Path

from bot.commands import (
    cancel_job,
    enqueue_job,
    get_job_for_chat,
    init_db,
    is_in_scope,
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
