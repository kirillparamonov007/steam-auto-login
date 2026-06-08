"""Управление конфигурацией accounts.json и settings."""

import json
from pathlib import Path


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "accounts.json"


def load_config():
    """Загрузить конфиг из accounts.json."""
    if not CONFIG_PATH.exists():
        return {
            "accounts": [],
            "settings": {
                "steam_exe_path": "C:\\Program Files (x86)\\Steam\\steam.exe",
                "game_app_id": "420980",  # Bongo Cat
                "game_launch_delay": 10,  # секунд
                "mafiles_dir": "mafiles",
            },
        }
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config):
    """Сохранить конфиг в accounts.json."""
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_base_dir():
    """Вернуть базовую директорию программы."""
    return BASE_DIR
