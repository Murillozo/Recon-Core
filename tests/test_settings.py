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


def test_load_settings_with_relative_paths(tmp_path, monkeypatch):
    project_root = tmp_path / "recon-core"
    project_root.mkdir()
    cfg = project_root / "config" / "app.yml"
    cfg.parent.mkdir()
    cfg.write_text(
        """
app:
  recon_root: ""
paths:
  sqlite: storage/history.sqlite
  scope: config/scope.txt
  tools: config/tools.yml
  profiles: config/profiles
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("RECON_ROOT", str(project_root))
    monkeypatch.setenv("RECON_CONFIG_FILE", str(cfg))
    settings = load_settings()

    assert settings.recon_root == project_root
    assert settings.sqlite_path == project_root / "storage" / "history.sqlite"
    assert settings.scope_file == project_root / "config" / "scope.txt"
    assert settings.tools_file == project_root / "config" / "tools.yml"
    assert settings.profiles_dir == project_root / "config" / "profiles"
