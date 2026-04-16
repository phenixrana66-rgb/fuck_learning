import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.common.config import get_settings


class ConfigSettingsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
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

    def test_local_config_reads_new_uppercase_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_config = Path(tmp) / "config.local.py"
            local_config.write_text(
                "APPID = 'voice-app-id'\n"
                "ACCESS_TOKEN = 'voice-access-token'\n"
                "CLUSTER = 'volcano_tts'\n"
                "VOICE_TYPE = 'zh_male_M392_conversation_wvae_bigtts'\n",
                encoding="utf-8",
            )
            with patch("backend.app.common.config._LOCAL_CONFIG_PATH", local_config):
                settings = get_settings()

        self.assertEqual(settings.APPID, "voice-app-id")
        self.assertEqual(settings.ACCESS_TOKEN, "voice-access-token")
        self.assertEqual(settings.CLUSTER, "volcano_tts")
        self.assertEqual(settings.VOICE_TYPE, "zh_male_M392_conversation_wvae_bigtts")

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
