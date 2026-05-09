from pathlib import Path

import pytest

from bot import controller
from recon_settings import AppSettings


class _DummyApp:
    def add_handler(self, _handler):
        return None

    def run_polling(self, close_loop=False):
        assert close_loop is False


class _DummyBuilder:
    def __init__(self):
        self.received_token = None

    def token(self, token: str):
        self.received_token = token
        return self

    def build(self):
        return _DummyApp()


class _DummyApplication:
    @staticmethod
    def builder():
        return _DummyBuilder()


def _settings(token: str | None) -> AppSettings:
    root = Path("/tmp/recon-core")
    return AppSettings(
        config_file=root / "config" / "app.yml",
        recon_root=root,
        recon_output_dir=root / "storage" / "recon",
        telegram_bot_token=token,
        worker_poll_seconds=15,
        sqlite_path=root / "storage" / "history.sqlite",
        scope_file=root / "config" / "scope.txt",
        tools_file=root / "config" / "tools.yml",
        profiles_dir=root / "config" / "profiles",
    )


def test_main_without_token_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(controller, "load_settings", lambda: _settings(None))

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        controller.main()


def test_main_with_token_starts_polling(monkeypatch):
    monkeypatch.setattr(controller, "load_settings", lambda: _settings("test-token"))
    monkeypatch.setattr(
        controller,
        "environment_paths",
        lambda: {"db": Path("/tmp/db.sqlite"), "root": Path("/tmp"), "recon_output": Path("/tmp/storage/recon")},
    )
    monkeypatch.setattr(controller, "init_db", lambda _db: None)
    monkeypatch.setattr(controller, "Application", _DummyApplication)

    controller.main()


def test_single_instance_lock_raises_when_already_locked(monkeypatch, tmp_path):
    lock_file = tmp_path / "bot.lock"

    def _fake_flock(_fd, operation):
        if operation == (controller.fcntl.LOCK_EX | controller.fcntl.LOCK_NB):
            raise BlockingIOError("already locked")

    monkeypatch.setattr(controller.fcntl, "flock", _fake_flock)

    with pytest.raises(RuntimeError, match="already running"):
        with controller.single_instance_lock(lock_file):
            pass


def test_recon_output_status_message_ok(monkeypatch, tmp_path):
    recon_dir = tmp_path / "storage" / "recon"
    recon_dir.mkdir(parents=True)
    monkeypatch.setattr(controller, "environment_paths", lambda: {"recon_output": recon_dir})

    message = controller.recon_output_status_message()
    assert "recon_output válido" in message
    assert str(recon_dir) in message


def test_recon_output_status_message_when_file(monkeypatch, tmp_path):
    not_dir = tmp_path / "recon-output.txt"
    not_dir.write_text("x", encoding="utf-8")
    monkeypatch.setattr(controller, "environment_paths", lambda: {"recon_output": not_dir})

    message = controller.recon_output_status_message()
    assert "inválido" in message


def test_recon_output_status_message_missing(monkeypatch, tmp_path):
    missing = tmp_path / "missing" / "recon"
    monkeypatch.setattr(controller, "environment_paths", lambda: {"recon_output": missing})

    message = controller.recon_output_status_message()
    assert "não encontrado" in message
