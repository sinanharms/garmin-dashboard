from pathlib import Path

from pydantic import Field, PositiveInt, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", case_sensitive=False)

    garmin_email: str = Field(min_length=1, validation_alias="GARMIN_EMAIL")
    garmin_password: SecretStr = Field(validation_alias="GARMIN_PASSWORD")
    garmin_token_dir: Path = Field(validation_alias="GARMIN_TOKEN_DIR")
    database_path: Path = Field(validation_alias="DATABASE_PATH")
    backup_dir: Path = Field(validation_alias="BACKUP_DIR")
    garmin_mcp_command: str = Field(min_length=1, validation_alias="GARMIN_MCP_COMMAND")
    mcp_timeout_seconds: PositiveInt = Field(validation_alias="MCP_TIMEOUT_SECONDS")
    backup_retention_count: PositiveInt = Field(validation_alias="BACKUP_RETENTION_COUNT")
    backup_retention_days: PositiveInt = Field(validation_alias="BACKUP_RETENTION_DAYS")

    @field_validator("garmin_password")
    @classmethod
    def reject_empty_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("GARMIN_PASSWORD must not be empty")
        return value
