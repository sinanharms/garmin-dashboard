import pytest
from pydantic import ValidationError

from garmin_dashboard.config import Settings


def set_required_environment(monkeypatch, tmp_path):
    values = {
        "GARMIN_EMAIL": "athlete@example.test",
        "GARMIN_PASSWORD": "secret",
        "GARMIN_TOKEN_DIR": str(tmp_path / "tokens"),
        "DATABASE_PATH": str(tmp_path / "dashboard.sqlite3"),
        "BACKUP_DIR": str(tmp_path / "backups"),
        "GARMIN_MCP_COMMAND": "garmin-mcp",
        "MCP_TIMEOUT_SECONDS": "30",
        "BACKUP_RETENTION_COUNT": "7",
        "BACKUP_RETENTION_DAYS": "31",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_settings_reads_required_environment(monkeypatch, tmp_path):
    set_required_environment(monkeypatch, tmp_path)

    settings = Settings()

    assert settings.garmin_email == "athlete@example.test"
    assert settings.garmin_password.get_secret_value() == "secret"
    assert "secret" not in repr(settings)


def test_settings_rejects_missing_garmin_password(monkeypatch, tmp_path):
    set_required_environment(monkeypatch, tmp_path)
    monkeypatch.delenv("GARMIN_PASSWORD")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_extra_values(monkeypatch, tmp_path):
    set_required_environment(monkeypatch, tmp_path)

    with pytest.raises(ValidationError):
        Settings(unexpected_setting="value")  # ty: ignore[unknown-argument]


def test_settings_rejects_empty_garmin_password(monkeypatch, tmp_path):
    set_required_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("GARMIN_PASSWORD", "")

    with pytest.raises(ValidationError):
        Settings()
