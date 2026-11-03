"""
Unit tests for application configuration.

Tests cover settings loading, defaults, field validation, and the settings
singleton behaviour. No external services are required.
"""

from __future__ import annotations

import pytest

from regularag.core.config import AppSettings, get_settings


@pytest.mark.unit
class TestAppSettingsDefaults:
    """Verify default configuration values are sensible."""

    def test_default_app_name(self) -> None:
        settings = AppSettings()
        assert settings.app_name == "RegulaRAG"

    def test_default_environment(self) -> None:
        settings = AppSettings()
        assert settings.app_env == "development"

    def test_default_debug_is_false(self) -> None:
        settings = AppSettings()
        assert settings.app_debug is False

    def test_default_api_port(self) -> None:
        settings = AppSettings()
        assert settings.api_port == 8000

    def test_default_api_host(self) -> None:
        settings = AppSettings()
        assert settings.api_host == "0.0.0.0"

    def test_default_api_prefix(self) -> None:
        settings = AppSettings()
        assert settings.api_prefix == "/api/v1"

    def test_default_log_level(self) -> None:
        settings = AppSettings()
        assert settings.log_level == "INFO"

    def test_default_log_format(self) -> None:
        settings = AppSettings()
        assert settings.log_format == "console"

    def test_default_version(self) -> None:
        settings = AppSettings()
        assert settings.app_version == "0.1.0"

    def test_default_ingestion_settings(self) -> None:
        settings = AppSettings()
        assert str(settings.ingestion_raw_storage_dir).replace("\\", "/").endswith("data/raw")
        assert settings.ingestion_http_timeout_connect == 10.0
        assert settings.ingestion_http_timeout_read == 60.0
        assert settings.ingestion_max_retries == 3
        assert settings.ingestion_backoff_factor == 2.0
        assert settings.ingestion_request_rate_limit == 1.0
        assert "RegulaRAG-Bot" in settings.ingestion_user_agent


@pytest.mark.unit
class TestAppSettingsEnvironmentOverride:
    """Verify that environment variables override defaults."""

    def test_override_app_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        settings = AppSettings()
        assert settings.app_env == "production"

    def test_override_debug(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_DEBUG", "true")
        settings = AppSettings()
        assert settings.app_debug is True

    def test_override_api_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_PORT", "9000")
        settings = AppSettings()
        assert settings.api_port == 9000

    def test_override_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = AppSettings()
        assert settings.log_level == "DEBUG"

    def test_override_ingestion_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INGESTION_MAX_RETRIES", "5")
        monkeypatch.setenv("INGESTION_REQUEST_RATE_LIMIT", "0.5")
        settings = AppSettings()
        assert settings.ingestion_max_retries == 5
        assert settings.ingestion_request_rate_limit == 0.5


@pytest.mark.unit
class TestAppSettingsValidation:
    """Verify field validation rules."""

    def test_invalid_app_env_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AppSettings(app_env="invalid_environment")  # type: ignore[arg-type]

    def test_invalid_log_level_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AppSettings(log_level="VERBOSE")  # type: ignore[arg-type]

    def test_api_port_must_be_positive(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AppSettings(api_port=0)

    def test_api_port_must_be_within_range(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AppSettings(api_port=99999)


@pytest.mark.unit
class TestAppSettingsProperties:
    """Verify computed properties return correct values."""

    def test_is_production_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        settings = AppSettings()
        assert settings.is_production is True

    def test_is_production_false_in_development(self) -> None:
        settings = AppSettings()
        assert settings.is_production is False

    def test_cors_origins_list_parsed(self) -> None:
        settings = AppSettings(cors_origins="http://localhost:3000,http://localhost:5173")
        origins = settings.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
        assert len(origins) == 2

    def test_effective_database_url_uses_explicit_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        custom_url = "postgresql+asyncpg://user:pass@dbhost:5432/mydb"
        monkeypatch.setenv("DATABASE_URL", custom_url)
        settings = AppSettings()
        assert settings.effective_database_url == custom_url

    def test_effective_database_url_constructed_from_parts(self) -> None:
        settings = AppSettings(
            postgres_user="testuser",
            postgres_password="test_password_value",  # noqa: S106
            postgres_host="dbhost",
            postgres_port=5432,
            postgres_db="testdb",
        )
        url = settings.effective_database_url
        assert "testuser" in url
        assert "dbhost" in url
        assert "testdb" in url


@pytest.mark.unit
class TestSettingsSingleton:
    """Verify the settings singleton caching behaviour."""

    def test_get_settings_returns_same_instance(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_settings_returns_app_settings_instance(self) -> None:
        settings = get_settings()
        assert isinstance(settings, AppSettings)
