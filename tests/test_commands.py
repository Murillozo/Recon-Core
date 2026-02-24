from pathlib import Path

from bot.commands import is_in_scope, load_scope, validate_domain


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
