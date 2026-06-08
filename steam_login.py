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


def find_mafile_by_login(login, mafiles_dir):
    """Найти .maFile по логину аккаунта в директории mafiles.
    
    Ищет файл с именем вида: {login}.maFile
    """
    mafiles_path = Path(mafiles_dir)
    if not mafiles_path.exists():
        raise FileNotFoundError(f"Папка mafiles не найдена: {mafiles_path}")
    
    # Ищем файл: login.maFile
    mafile = mafiles_path / f"{login}.maFile"
    if mafile.exists():
        return str(mafile)
    
    # Если не нашли точное совпадение, показываем что есть
    existing_files = list(mafiles_path.glob("*.maFile"))
    if existing_files:
        files_list = ", ".join([f.name for f in existing_files])
        raise FileNotFoundError(
            f"maFile для аккаунта '{login}' не найден.\n"
            f"Ищу: {login}.maFile\n"
            f"Найдено в папке: {files_list}"
        )
    else:
        raise FileNotFoundError(
            f"Папка mafiles пуста. Положите файл {login}.maFile туда."
        )


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


def login_steam_only(
    steam_exe,
    login,
    password,
    mafiles_dir,
    pre_login_delay=15,
    login_hold_delay=10,
    status_callback=None,
):
    """Запустить Steam и залогиниться БЕЗ запуска игры.

    Args:
        steam_exe: путь к steam.exe
        login: Steam логин
        password: Steam пароль
        mafiles_dir: директория с .maFile файлами
        pre_login_delay: задержка ДО ввода логина/пароля (дает время на загрузку Steam)
        login_hold_delay: задержка ПОСЛЕ ввода логина (сколько держать Steam открытым)
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

        # Найти .maFile по логину
        log(f"[{login}] Поиск .maFile в папке mafiles/...")
        mafile_path = find_mafile_by_login(login, mafiles_dir)
        log(f"[{login}] Найден: {Path(mafile_path).name}")

        # Получить Steam Guard код
        log(f"[{login}] Получение Steam Guard кода...")
        secs = seconds_until_next_code()
        if secs < 5:
            log(f"[{login}] Ожидание свежего кода ({secs}с)...")
            time.sleep(secs + 1)

        code = code_from_mafile(mafile_path)
        log(f"[{login}] Код получен: {code}")

        # Запустить Steam с логином
        log(f"[{login}] Запуск Steam...")
        subprocess.Popen(f'"{steam_exe}"')
        log(f"[{login}] Ожидание загрузки Steam ({pre_login_delay}с)...")
        time.sleep(pre_login_delay)
        
        log(f"[{login}] Ввод логина/пароля/кода...")
        steam_cmd = f'"{steam_exe}" -login {login} {password} -steamguard {code}'
        subprocess.Popen(steam_cmd, shell=True)

        # Держать Steam открытым
        log(f"[{login}] Steam залогинен, ждем {login_hold_delay}с...")
        time.sleep(login_hold_delay)

        # Выход
        log(f"[{login}] Закрытие Steam...")
        kill_steam_processes()
        time.sleep(1)

        log(f"[{login}] ✓ Завершено")

    except Exception as e:
        log(f"[{login}] ✗ Ошибка: {e}")
        raise


def login_and_launch_game(
    steam_exe,
    login,
    password,
    app_id,
    mafiles_dir,
    pre_login_delay=15,
    steam_startup_delay=40,
    game_launch_delay=10,
    status_callback=None,
):
    """Логин в Steam, запуск игры и ожидание.

    Args:
        steam_exe: путь к steam.exe
        login: Steam логин
        password: Steam пароль
        app_id: App ID игры (например, 420980 для Bongo Cat)
        mafiles_dir: директория с .maFile файлами
        pre_login_delay: задержка ДО ввода логина/пароля (дает время на загрузку Steam)
        steam_startup_delay: задержка между вводом кода и запуском игры
        game_launch_delay: задержка ПОСЛЕ запуска игры (время в игре)
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

        # Найти .maFile по логину
        log(f"[{login}] Поиск .maFile в папке mafiles/...")
        mafile_path = find_mafile_by_login(login, mafiles_dir)
        log(f"[{login}] Найден: {Path(mafile_path).name}")

        # Получить Steam Guard код
        log(f"[{login}] Получение Steam Guard кода...")
        secs = seconds_until_next_code()
        if secs < 5:
            log(f"[{login}] Ожидание свежего кода ({secs}с)...")
            time.sleep(secs + 1)

        code = code_from_mafile(mafile_path)
        log(f"[{login}] Код получен: {code}")

        # Запустить Steam
        log(f"[{login}] Запуск Steam...")
        subprocess.Popen(f'"{steam_exe}"')
        log(f"[{login}] Ожидание загрузки Steam ({pre_login_delay}с)...")
        time.sleep(pre_login_delay)
        
        log(f"[{login}] Ввод логина/пароля/кода...")
        steam_cmd = f'"{steam_exe}" -login {login} {password} -steamguard {code}'
        subprocess.Popen(steam_cmd, shell=True)
        
        # Ожидание авторизации и загрузки Steam
        log(f"[{login}] Ожидание авторизации Steam ({steam_startup_delay}с)...")
        time.sleep(steam_startup_delay)

        # Запустить игру через App ID
        log(f"[{login}] Запуск игры (App ID: {app_id})...")
        subprocess.Popen(f"steam://run/{app_id}")

        # Ожидание игры
        log(f"[{login}] Игра запущена, ожидание {game_launch_delay}с...")
        time.sleep(game_launch_delay)

        # Выход
        log(f"[{login}] Закрытие Steam...")
        kill_steam_processes()
        time.sleep(1)

        log(f"[{login}] ✓ Завершено")

    except Exception as e:
        log(f"[{login}] ✗ Ошибка: {e}")
        raise
