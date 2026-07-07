"""
Tests para módulo de configuración (settings.py)
"""

import os
import sys
import pytest
from unittest.mock import patch


_CONFIG_MODULES = (
    "src.config",
    "src.config.settings",
)


def _reload_config():
    for key in _CONFIG_MODULES:
        sys.modules.pop(key, None)
    from src.config import ConfigView
    return ConfigView()


class TestConfig:
    """Tests para ConfigView / settings."""

    @pytest.fixture(autouse=True)
    def reset_config_module(self):
        saved = {key: sys.modules[key] for key in _CONFIG_MODULES if key in sys.modules}
        for key in _CONFIG_MODULES:
            sys.modules.pop(key, None)
        yield
        for key in _CONFIG_MODULES:
            sys.modules.pop(key, None)
        sys.modules.update(saved)

    @pytest.mark.unit
    def test_config_loads_from_env(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "testing", "DEBUG": "True", "SECRET_KEY": "test-key"}):
            config = _reload_config()
            assert config.ENVIRONMENT == "testing"
            assert config.DEBUG is True

    @pytest.mark.unit
    def test_config_defaults(self):
        with patch.dict(os.environ, {"SECRET_KEY": "test-key"}):
            config = _reload_config()
            assert config.LOG_LEVEL in ["INFO", "DEBUG"]
            assert config.DB_HOST == "localhost"

    @pytest.mark.unit
    def test_database_url_construction(self):
        with patch.dict(os.environ, {
            "SECRET_KEY": "test-key",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_pass",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "testdb",
        }):
            config = _reload_config()
            expected = "postgresql://test_user:test_pass@localhost:5432/testdb"
            assert config.DATABASE_URL == expected

    @pytest.mark.unit
    def test_security_error_on_missing_secret_key(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "SECRET_KEY": ""}):
            with pytest.raises(ValueError, match="SECRET_KEY"):
                _reload_config()

    @pytest.mark.unit
    def test_config_to_dict_excludes_secrets(self):
        with patch.dict(os.environ, {"SECRET_KEY": "test-key"}):
            _reload_config()
            from src.config import ConfigView
            config_dict = ConfigView.to_dict(exclude_secrets=True)
            assert "SECRET_KEY" not in config_dict
            assert "DB_PASSWORD" not in config_dict

    @pytest.mark.unit
    def test_config_validate_passes(self):
        with patch.dict(os.environ, {"SECRET_KEY": "test-key", "ENVIRONMENT": "development"}):
            _reload_config()
            from src.config import ConfigView
            ConfigView.validate()
