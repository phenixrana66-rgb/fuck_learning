import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.common.config import get_settings


class ConfigSettingsTestCase(unittest.TestCase):
    env_keys = [
        "A12_APP_NAME",
        "A12_APP_VERSION",
        "A12_API_PREFIX",
        "A12_DEBUG",
        "A12_SIGNATURE_ENABLED",
        "A12_DB_URL",
        "A12_DB_HOST",
        "A12_DB_PORT",
        "A12_DB_USER",
        "A12_DB_PASSWORD",
        "A12_DB_NAME",
        "A12_DB_ECHO",
        "A12_LLM_API_BASE_URL",
        "A12_LLM_API_KEY",
        "A12_LLM_MODEL",
        "A12_LLM_TIMEOUT_SECONDS",
    ]

    def setUp(self) -> None:
        self.original_env = {key: os.environ.get(key) for key in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
        get_settings.cache_clear()

    def tearDown(self) -> None:
        for key in self.env_keys:
            os.environ.pop(key, None)
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
        get_settings.cache_clear()

    def test_missing_local_config_keeps_default_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_config = Path(tmp) / "config.local.py"
            with patch("backend.app.common.config._LOCAL_CONFIG_PATH", local_config):
                settings = get_settings()

        self.assertEqual(settings.db_host, "127.0.0.1")
        self.assertIsNone(settings.llm_api_key)

    def test_local_config_overrides_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_config = Path(tmp) / "config.local.py"
            local_config.write_text(
                "db_host = '192.168.0.10'\n"
                "db_port = 3307\n"
                "debug = False\n"
                "llm_api_key = 'local-key'\n",
                encoding="utf-8",
            )
            with patch("backend.app.common.config._LOCAL_CONFIG_PATH", local_config):
                settings = get_settings()

        self.assertEqual(settings.db_host, "192.168.0.10")
        self.assertEqual(settings.db_port, 3307)
        self.assertFalse(settings.debug)
        self.assertEqual(settings.llm_api_key, "local-key")

    def test_environment_variables_override_local_config(self) -> None:
        os.environ["A12_DB_HOST"] = "env-host"
        os.environ["A12_DEBUG"] = "true"
        os.environ["A12_LLM_API_KEY"] = "env-key"

        with tempfile.TemporaryDirectory() as tmp:
            local_config = Path(tmp) / "config.local.py"
            local_config.write_text(
                "db_host = 'local-host'\n"
                "debug = False\n"
                "llm_api_key = 'local-key'\n",
                encoding="utf-8",
            )
            with patch("backend.app.common.config._LOCAL_CONFIG_PATH", local_config):
                settings = get_settings()

        self.assertEqual(settings.db_host, "env-host")
        self.assertTrue(settings.debug)
        self.assertEqual(settings.llm_api_key, "env-key")

    def test_unknown_local_config_keys_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_config = Path(tmp) / "config.local.py"
            local_config.write_text(
                "db_name = 'local_db'\n"
                "unknown_value = 'should-be-ignored'\n",
                encoding="utf-8",
            )
            with patch("backend.app.common.config._LOCAL_CONFIG_PATH", local_config):
                settings = get_settings()

        self.assertEqual(settings.db_name, "local_db")
        self.assertFalse(hasattr(settings, "unknown_value"))
