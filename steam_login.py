"""Логин в Steam клиент, запуск игры и управление процессами."""

import os
import subprocess
import time
from pathlib import Path

from mafile import code_from_mafile, seconds_until_next_code


def find_steam_exe(custom_path=""):
    """Найти steam.exe в системе."""
    if custom_path and Path(custom_path).exists():
        return custom_path

    common_paths = [
        Path("C:/Program Files (x86)/Steam/steam.exe"),
        Path("C:/Program Files/Steam/steam.exe"),
        Path("D:/Steam/steam.exe"),
        Path("E:/Steam/steam.exe"),
    ]

    for path in common_paths:
        if path.exists():
            return str(path)

    # Проверить через реестр (Windows)
    try:
        import winreg
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(reg, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        steam_exe = Path(steam_path) / "steam.exe"
        if steam_exe.exists():
            return str(steam_exe)
    except Exception:
        pass

    raise FileNotFoundError("steam.exe не найден")


def kill_steam_processes():
    """Убить все процессы Steam."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "steam.exe"],
            capture_output=True,
            timeout=5,
        )
        subprocess.run(
            ["taskkill", "/F", "/IM", "steamwebhelper.exe"],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        print(f"Ошибка при закрытии Steam: {e}")


def login_and_launch_game(
    steam_exe,
    login,
    password,
    app_id,
    get_code_func,
    launch_delay=10,
    status_callback=None,
):
    """Логин в Steam, запуск игры и ожидание.

    Args:
        steam_exe: путь к steam.exe
        login: Steam логин
        password: Steam пароль
        app_id: App ID игры (например, 420980 для Bongo Cat)
        get_code_func: функция для получения Steam Guard кода
        launch_delay: задержка в секундах после запуска игры
        status_callback: функция для логирования статуса
    """

    def log(msg):
        if status_callback:
            status_callback(msg)
        print(msg)

    try:
        # Убить старые процессы Steam
        log(f"[{login}] Закрытие старых процессов Steam...")
        kill_steam_processes()
        time.sleep(2)

        # Получить Steam Guard код
        log(f"[{login}] Получение Steam Guard кода...")
        secs = seconds_until_next_code()
        if secs < 5:
            log(f"[{login}] Ожидание свежего кода ({secs}с)...")
            time.sleep(secs + 1)

        code = get_code_func()
        log(f"[{login}] Код получен: {code}")

        # Запустить Steam с логином
        log(f"[{login}] Запуск Steam с логином...")
        steam_cmd = f'"{steam_exe}" -login {login} {password} -steamguard {code}'
        subprocess.Popen(steam_cmd, shell=True)
        time.sleep(3)  # Дать Steam время на запуск

        # Запустить игру через App ID
        log(f"[{login}] Запуск игры (App ID: {app_id})...")
        subprocess.Popen(f"steam://run/{app_id}")

        # Ожидание
        log(f"[{login}] Игра запущена, ожидание {launch_delay}с...")
        time.sleep(launch_delay)

        # Выход
        log(f"[{login}] Закрытие Steam...")
        kill_steam_processes()
        time.sleep(1)

        log(f"[{login}] ✓ Завершено")

    except Exception as e:
        log(f"[{login}] ✗ Ошибка: {e}")
        raise
