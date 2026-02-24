from recon_settings import load_settings


def test_load_settings_from_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / "app.yml"
    cfg.write_text(
        """
app:
  recon_root: /tmp/recon
telegram:
  bot_token: test-token
worker:
  poll_seconds: 42
paths:
  sqlite: /tmp/recon/storage/history.sqlite
  scope: /tmp/recon/config/scope.txt
  tools: /tmp/recon/config/tools.yml
  profiles: /tmp/recon/config/profiles
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("RECON_CONFIG_FILE", str(cfg))
    settings = load_settings()

    assert str(settings.recon_root) == "/tmp/recon"
    assert settings.telegram_bot_token == "test-token"
    assert settings.worker_poll_seconds == 42
