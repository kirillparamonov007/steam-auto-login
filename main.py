"""GUI панель для автоматического входа в Steam и запуска игры на нескольких аккаунтах."""

import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk, scrolledtext

from config import load_config, save_config, CONFIG_PATH, BASE_DIR
from mafile import code_from_mafile, seconds_until_next_code
from steam_login import find_steam_exe, login_and_launch_game, kill_steam_processes


class SteamAutoLoginApp:
    def __init__(self, root):
        self.root = root
        root.title("Steam Auto Login")
        root.geometry("1000x700")
        self.root.resizable(True, True)

        self.config = load_config()
        self.running = False
        self.account_vars = {}
        self.log_messages = []

        self._build_ui()
        self._load_accounts()

    def _build_ui(self):
        """Построить интерфейс."""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Левая колонка: список аккаунтов
        left_frame = ttk.LabelFrame(main_frame, text="Аккаунты", padding=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Кнопки управления аккаунтами
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill="x", padx=0, pady=(0, 10))
        ttk.Button(btn_frame, text="Выбрать все", command=self._select_all).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Снять все", command=self._deselect_all).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Добавить", command=self._add_account).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Удалить", command=self._delete_account).pack(
            side="left", padx=2
        )

        # Список аккаунтов с прокруткой
        accounts_scroll = ttk.Frame(left_frame)
        accounts_scroll.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(accounts_scroll)
        scrollbar.pack(side="right", fill="y")

        self.accounts_frame = ttk.Frame(accounts_scroll)
        self.accounts_canvas = tk.Canvas(
            accounts_scroll, yscrollcommand=scrollbar.set, bg="white"
        )
        scrollbar.config(command=self.accounts_canvas.yview)
        self.accounts_canvas.pack(side="left", fill="both", expand=True)

        self.accounts_inner = ttk.Frame(self.accounts_canvas, padding=5)
        self.canvas_window = self.accounts_canvas.create_window(
            0, 0, window=self.accounts_inner, anchor="nw"
        )
        self.accounts_canvas.bind(
            "<Configure>",
            lambda e: self.accounts_canvas.itemconfig(
                self.canvas_window, width=e.width
            ),
        )

        # Правая колонка: настройки и логи
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Настройки
        settings_frame = ttk.LabelFrame(right_frame, text="Настройки", padding=10)
        settings_frame.pack(fill="x", padx=0, pady=(0, 10))

        ttk.Label(settings_frame, text="Путь к steam.exe:").grid(
            row=0, column=0, sticky="w", padx=(0, 5), pady=5
        )
        self.steam_path_var = tk.StringVar(
            value=self.config.get("settings", {}).get("steam_exe_path", "")
        )
        steam_entry = ttk.Entry(settings_frame, textvariable=self.steam_path_var)
        steam_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=5)
        ttk.Button(
            settings_frame, text="...", command=self._browse_steam, width=3
        ).grid(row=0, column=2, padx=(0, 5), pady=5)

        ttk.Label(settings_frame, text="App ID игры:").grid(
            row=1, column=0, sticky="w", padx=(0, 5), pady=5
        )
        self.app_id_var = tk.StringVar(
            value=self.config.get("settings", {}).get("game_app_id", "420980")
        )
        ttk.Entry(settings_frame, textvariable=self.app_id_var).grid(
            row=1, column=1, sticky="ew", padx=(0, 5), pady=5
        )

        ttk.Label(settings_frame, text="Задержка (сек):").grid(
            row=2, column=0, sticky="w", padx=(0, 5), pady=5
        )
        self.delay_var = tk.StringVar(
            value=str(
                self.config.get("settings", {}).get("game_launch_delay", 10)
            )
        )
        ttk.Entry(settings_frame, textvariable=self.delay_var).grid(
            row=2, column=1, sticky="ew", padx=(0, 5), pady=5
        )

        settings_frame.columnconfigure(1, weight=1)

        # Кнопки запуска
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill="x", padx=0, pady=(0, 10))
        self.start_btn = ttk.Button(
            action_frame,
            text="▶ Запустить",
            command=self._start_login_sequence,
            state="normal",
        )
        self.start_btn.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.stop_btn = ttk.Button(
            action_frame,
            text="⏹ Остановить",
            command=self._stop_login_sequence,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 5), fill="x", expand=True)
        ttk.Button(action_frame, text="⚙ Сохранить", command=self._save_settings).pack(
            side="left", fill="x", expand=True
        )

        # Логи
        logs_frame = ttk.LabelFrame(right_frame, text="Логи", padding=10)
        logs_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(
            logs_frame, height=15, width=50, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

    def _load_accounts(self):
        """Загрузить список аккаунтов из конфига."""
        for widget in self.accounts_inner.winfo_children():
            widget.destroy()

        self.account_vars = {}
        for acc in self.config.get("accounts", []):
            var = tk.BooleanVar(value=False)
            self.account_vars[acc["login"]] = var

            frame = ttk.Frame(self.accounts_inner, relief="solid", borderwidth=1)
            frame.pack(fill="x", padx=5, pady=3)

            ttk.Checkbutton(frame, text=f"{acc['label']}", variable=var).pack(
                side="left", padx=5, pady=5
            )
            ttk.Label(frame, text=f"({acc['login']})", foreground="gray").pack(
                side="left", padx=5, pady=5
            )

        self.accounts_canvas.configure(
            scrollregion=self.accounts_canvas.bbox("all")
        )

    def _log(self, message):
        """Добавить сообщение в лог."""
        self.log_messages.append(message)
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        print(message)

    def _select_all(self):
        """Выбрать все аккаунты."""
        for var in self.account_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Снять выделение со всех аккаунтов."""
        for var in self.account_vars.values():
            var.set(False)

    def _browse_steam(self):
        """Выбрать steam.exe через диалог."""
        path = filedialog.askopenfilename(
            title="Выбери steam.exe",
            filetypes=[("Exe files", "*.exe"), ("All files", "*.*")],
            initialfile="steam.exe",
        )
        if path:
            self.steam_path_var.set(path)

    def _add_account(self):
        """Добавить новый аккаунт."""
        dialog = AccountDialog(self.root, on_save=self._on_account_added)

    def _delete_account(self):
        """Удалить выбранный аккаунт."""
        selected = [login for login, var in self.account_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Внимание", "Выбери аккаунт для удаления")
            return

        if messagebox.askyesno("Удалить", f"Удалить {len(selected)} аккаунт(ов)?"):
            self.config["accounts"] = [
                acc
                for acc in self.config["accounts"]
                if acc["login"] not in selected
            ]
            save_config(self.config)
            self._load_accounts()
            self._log(f"Удалено {len(selected)} аккаунт(ов)")

    def _on_account_added(self, account_data):
        """Обработка добавления нового аккаунта."""
        self.config.setdefault("accounts", []).append(account_data)
        save_config(self.config)
        self._load_accounts()
        self._log(f"Добавлен аккаунт: {account_data['label']}")

    def _save_settings(self):
        """Сохранить настройки."""
        try:
            delay = int(self.delay_var.get())
            if delay < 1:
                raise ValueError("Задержка должна быть >= 1")
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверная задержка: {e}")
            return

        self.config["settings"] = {
            "steam_exe_path": self.steam_path_var.get(),
            "game_app_id": self.app_id_var.get(),
            "game_launch_delay": delay,
            "mafiles_dir": self.config["settings"].get("mafiles_dir", "mafiles"),
        }
        save_config(self.config)
        messagebox.showinfo("Успех", "Настройки сохранены")
        self._log("Настройки сохранены")

    def _start_login_sequence(self):
        """Начать последовательный вход в аккаунты."""
        selected_logins = [
            login for login, var in self.account_vars.items() if var.get()
        ]
        if not selected_logins:
            messagebox.showwarning("Внимание", "Выбери хотя бы один аккаунт")
            return

        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._log(
            f"\n=== Запуск последовательности для {len(selected_logins)} аккаунт(ов) ==="
        )

        thread = threading.Thread(
            target=self._login_sequence_worker, args=(selected_logins,), daemon=True
        )
        thread.start()

    def _stop_login_sequence(self):
        """Остановить последовательность."""
        self.running = False
        self._log("\nОстановка...")
        kill_steam_processes()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _login_sequence_worker(self, selected_logins):
        """Рабочий поток для последовательного входа."""
        try:
            steam_exe = find_steam_exe(
                self.config["settings"].get("steam_exe_path", "")
            )
            app_id = self.config["settings"].get("game_app_id", "420980")
            delay = self.config["settings"].get("game_launch_delay", 10)
            mafiles_dir = BASE_DIR / self.config["settings"].get(
                "mafiles_dir", "mafiles"
            )

            for login in selected_logins:
                if not self.running:
                    break

                acc = next(
                    (a for a in self.config["accounts"] if a["login"] == login), None
                )
                if not acc:
                    continue

                try:
                    # Получить функцию для кода
                    mafile_path = acc.get("mafile")
                    if not mafile_path:
                        raise ValueError("maFile не указан")

                    full_mafile_path = mafiles_dir / Path(mafile_path).name
                    if not full_mafile_path.exists():
                        raise FileNotFoundError(f"maFile не найден: {full_mafile_path}")

                    def get_code():
                        return code_from_mafile(str(full_mafile_path))

                    # Логин и запуск
                    login_and_launch_game(
                        steam_exe,
                        login,
                        acc["password"],
                        app_id,
                        get_code,
                        launch_delay=delay,
                        status_callback=self._log,
                    )

                except Exception as e:
                    self._log(f"✗ Ошибка для {login}: {e}")

                # Пауза перед следующим аккаунтом
                if self.running and login != selected_logins[-1]:
                    self._log("Ожидание перед следующим аккаунтом...")
                    time.sleep(2)

            self._log("\n=== Последовательность завершена ===")

        except Exception as e:
            self._log(f"Критическая ошибка: {e}")
            messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")

        finally:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.running = False


class AccountDialog:
    """Диалог для добавления/редактирования аккаунта."""

    def __init__(self, parent, on_save):
        self.on_save = on_save

        win = tk.Toplevel(parent)
        win.title("Добавить аккаунт")
        win.geometry("450x350")
        win.transient(parent)
        win.grab_set()
        self.win = win

        win.columnconfigure(1, weight=1)

        def add_row(row, label, widget):
            ttk.Label(win, text=label).grid(
                row=row, column=0, sticky="w", padx=10, pady=6
            )
            widget.grid(row=row, column=1, padx=10, pady=6, sticky="ew")

        self.label_var = tk.StringVar()
        add_row(0, "Название:", ttk.Entry(win, textvariable=self.label_var))

        self.login_var = tk.StringVar()
        add_row(1, "Логин Steam:", ttk.Entry(win, textvariable=self.login_var))

        self.password_var = tk.StringVar()
        add_row(2, "Пароль:", ttk.Entry(win, textvariable=self.password_var, show="*"))

        # Выбор .maFile
        mafile_frame = ttk.Frame(win)
        self.mafile_var = tk.StringVar()
        ttk.Entry(mafile_frame, textvariable=self.mafile_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(mafile_frame, text="...", command=self._browse_mafile, width=3).pack(
            side="left", padx=3
        )
        add_row(3, "Выбери .maFile:", mafile_frame)

        hint = ttk.Label(
            win,
            text=".maFile должен лежать в папке 'mafiles' рядом с программой.",
            foreground="gray",
        )
        hint.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Кнопки
        btn_frame = ttk.Frame(win)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Сохранить", command=self._save).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Отмена", command=win.destroy).pack(
            side="left", padx=5
        )

    def _browse_mafile(self):
        """Выбрать .maFile."""
        path = filedialog.askopenfilename(
            title="Выбери .maFile",
            filetypes=[("Steam Mobile Authenticator", "*.maFile"), ("All files", "*.*")],
            initialdir=str(BASE_DIR / "mafiles"),
        )
        if path:
            self.mafile_var.set(Path(path).name)

    def _save(self):
        """Сохранить аккаунт."""
        if not self.label_var.get().strip():
            messagebox.showwarning("Внимание", "Введи название", parent=self.win)
            return
        if not self.login_var.get().strip():
            messagebox.showwarning("Внимание", "Введи логин Steam", parent=self.win)
            return
        if not self.mafile_var.get().strip():
            messagebox.showwarning("Внимание", "Выбери .maFile", parent=self.win)
            return

        data = {
            "label": self.label_var.get().strip(),
            "login": self.login_var.get().strip(),
            "password": self.password_var.get(),
            "mafile": self.mafile_var.get().strip(),
        }
        self.on_save(data)
        self.win.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SteamAutoLoginApp(root)
    root.mainloop()
