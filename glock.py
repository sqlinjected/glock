import sys
from collections import deque
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("glock runs on Windows.")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cursor_lock import CursorLock, SingleInstance, enable_dpi_awareness
from tray import TrayIcon


APP_DIR = Path(__file__).resolve().parent
ICON_PATH = APP_DIR / "assets" / "glock.ico"
SETTINGS_PATH = APP_DIR / "GameCursorLock.settings"
DEFAULT_GAME = "legouniverse.exe"


def executable_name(text: str) -> str | None:
    name = text.strip()
    if not name or name.lower() in {".", "..", ".exe"}:
        return None
    if any(character in '<>:"/\\|?*' or ord(character) < 32 for character in name):
        return None
    if not name.lower().endswith(".exe"):
        name += ".exe"
    return name if len(name.encode("utf-16-le")) <= 510 else None


class GlockApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cursor = CursorLock()
        self.executable = None
        self.settings_open = False
        self.paused = False
        self.closed = False
        self.timer = None
        self.tray_actions = deque()
        # The native window callback runs inside Tk's message pump. Handle its actions on a Tk timer.
        self.tray = TrayIcon(ICON_PATH, self.tray_actions.append)

    def start(self):
        self.build_settings()
        self.root.report_callback_exception = self.callback_error
        self.tray.start()
        try:
            self.executable = executable_name(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError) as error:
            messagebox.showwarning("glock", f"Could not read settings.\n\n{error}", parent=self.root)

        if self.executable is None:
            self.show_settings()
        self.tick()

    def build_settings(self):
        self.root.title("glock")
        self.root.iconbitmap(str(ICON_PATH))
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_settings)
        self.root.bind("<Escape>", lambda _event: self.hide_settings())

        frame = ttk.Frame(self.root, padding=20)
        frame.grid()
        ttk.Label(frame, text="Game executable").grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.name = tk.StringVar(master=self.root)
        self.name_entry = ttk.Entry(frame, width=34, textvariable=self.name)
        self.name_entry.grid(row=1, column=0, sticky="ew")
        self.name_entry.bind("<Return>", lambda _event: self.save_settings())
        ttk.Button(frame, text="Browse…", command=self.browse).grid(row=1, column=1, padx=(8, 0))

        if self.tray.hotkey_registered:
            hint = "Alt+Tab frees the mouse. Ctrl+Alt+F10 pauses or resumes the lock."
        else:
            hint = "Alt+Tab frees the mouse. Use the tray menu to pause the lock."
        ttk.Label(frame, text=hint, wraplength=340).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 15)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.hide_settings).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Start", command=self.save_settings).grid(row=0, column=1)

    def show_settings(self):
        if not self.settings_open:
            self.settings_open = True
            self.name.set(self.executable or DEFAULT_GAME)
            self.update_lock()
        self.root.deiconify()
        self.root.lift()
        self.name_entry.focus_set()
        self.name_entry.selection_range(0, tk.END)

    def hide_settings(self):
        self.root.withdraw()
        self.settings_open = False
        self.update_lock()

    def browse(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Choose your game", filetypes=[("Windows executables", "*.exe")]
        )
        if path:
            self.name.set(Path(path).name)

    def save_settings(self):
        name = executable_name(self.name.get())
        if name is None:
            messagebox.showwarning("glock", "Enter a game executable like legouniverse.exe.", parent=self.root)
            self.name_entry.focus_set()
            return

        try:
            temporary = SETTINGS_PATH.with_suffix(".settings.tmp")
            temporary.write_text(name + "\n", encoding="utf-8")
            temporary.replace(SETTINGS_PATH)
        except OSError as error:
            messagebox.showerror(
                "glock", f"Could not save settings next to glock.py.\n\n{error}", parent=self.root
            )
            return

        self.executable = name
        self.paused = False
        self.hide_settings()

    def handle_tray_action(self, action: str):
        if action == "settings":
            self.show_settings()
        elif action == "exit":
            self.close()
            self.root.quit()
        elif action == "toggle" and self.can_pause():
            self.paused = not self.paused

    def can_pause(self):
        return self.executable is not None and not self.settings_open

    def update_lock(self):
        if self.settings_open:
            self.cursor.release()
            status = "Settings open"
        elif self.executable is None:
            self.cursor.release()
            status = "Choose a game in Settings"
        elif self.paused:
            self.cursor.release()
            status = "Paused"
        else:
            status = self.cursor.update(self.executable)

        self.tray.update(status, self.paused, self.can_pause())

    def tick(self):
        self.timer = None
        while self.tray_actions and not self.closed:
            self.handle_tray_action(self.tray_actions.popleft())
        if not self.closed:
            self.update_lock()
            self.timer = self.root.after(75, self.tick)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.timer is not None:
            self.root.after_cancel(self.timer)
        self.cursor.release()
        self.tray.close()

    def callback_error(self, _error_type, error, _traceback):
        self.close()
        try:
            messagebox.showerror("glock", str(error), parent=self.root)
        finally:
            self.root.quit()


def main():
    enable_dpi_awareness()
    with SingleInstance() as first_instance:
        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            if not first_instance:
                messagebox.showinfo("glock", "glock is already running in the tray.", parent=root)
                return
            app = GlockApp(root)
            app.start()
            root.mainloop()
        except (OSError, tk.TclError) as error:
            if app is not None:
                app.close()
            messagebox.showerror("glock", str(error), parent=root)
        finally:
            if app is not None:
                app.close()
            root.destroy()


if __name__ == "__main__":
    main()
