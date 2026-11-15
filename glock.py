import sys
from collections import deque
from pathlib import Path
from time import monotonic

if sys.platform != "win32":
    raise SystemExit("glock runs on Windows.")

import tkinter as tk
from tkinter import messagebox

from cursor_lock import CursorLock, SingleInstance, connected_displays, enable_dpi_awareness
from hotkey import DEFAULT_HOTKEY, Hotkey, parse_hotkey
from panel import BoomchikaPanel
from tray import TrayIcon


APP_DIR = Path(__file__).resolve().parent
ICON_PATH = APP_DIR / "assets" / "glock.ico"
LOGO_PATH = APP_DIR / "assets" / "glock.png"
SETTINGS_PATH = APP_DIR / "GameCursorLock.settings"
HOTKEY_PATH = APP_DIR / "glock.hotkey"
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


def write_setting(path: Path, value: str):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value + "\n", encoding="utf-8")
    temporary.replace(path)


class GlockApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cursor = CursorLock()
        self.executable = None
        self.panel_visible = False
        self.displays = ()
        self.next_display_check = 0.0
        self.paused = False
        self.closed = False
        self.timer = None
        self.tray_actions = deque()
        # The native window callback runs inside Tk's message pump. Handle its actions on a Tk timer.
        self.tray = TrayIcon(ICON_PATH, self.tray_actions.append, self.load_hotkey())

    def load_hotkey(self) -> Hotkey:
        try:
            return parse_hotkey(HOTKEY_PATH.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError, ValueError) as error:
            messagebox.showwarning(
                "boomchikaUI", f"Using {DEFAULT_HOTKEY.label} for now. Could not load the saved shortcut.\n\n{error}",
                parent=self.root,
            )
        return DEFAULT_HOTKEY

    def start(self):
        self.build_panel()
        self.root.report_callback_exception = self.callback_error
        self.tray.start()
        try:
            self.executable = executable_name(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError) as error:
            messagebox.showwarning("glock", f"Could not read settings.\n\n{error}", parent=self.root)

        if self.executable is None:
            self.show_panel()
        self.tick()

    def build_panel(self):
        self.root.title("boomchikaUI")
        self.root.iconbitmap(str(ICON_PATH))
        self.root.protocol("WM_DELETE_WINDOW", self.hide_panel)
        self.root.bind("<Escape>", lambda _event: self.hide_panel())
        self.panel = BoomchikaPanel(
            self.root, LOGO_PATH, self.tray.hotkey, self.tray.hotkey_registered,
            self.save_game, self.toggle_pause, self.save_hotkey,
        )
        self.panel.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.root.minsize(self.root.winfo_reqwidth(), self.root.winfo_reqheight())

    def show_panel(self):
        already_visible = self.panel_visible
        self.root.deiconify()
        self.root.lift()
        if not already_visible:
            self.panel_visible = True
            self.next_display_check = 0.0
            self.panel.edit_game(self.executable or DEFAULT_GAME, focus=self.executable is None)
            self.update_lock()

    def hide_panel(self):
        self.panel_visible = False
        self.root.withdraw()
        self.update_lock()

    def save_game(self, text):
        name = executable_name(text)
        if name is None:
            messagebox.showwarning("boomchikaUI", "Enter a game executable like legouniverse.exe.", parent=self.root)
            self.panel.entry.focus_set()
            return

        try:
            write_setting(SETTINGS_PATH, name)
        except OSError as error:
            messagebox.showerror(
                "glock", f"Could not save settings next to glock.py.\n\n{error}", parent=self.root
            )
            return

        self.executable = name
        self.panel.edit_game(name)
        self.update_lock()

    def save_hotkey(self, hotkey: Hotkey) -> str | None:
        try:
            if not self.tray.change_hotkey(hotkey, lambda: write_setting(HOTKEY_PATH, hotkey.label)):
                return f"{hotkey.label} is unavailable. Try another shortcut."
        except OSError as error:
            return f"Could not save the shortcut. {error}"
        self.panel.set_hotkey(self.tray.hotkey, self.tray.hotkey_registered)
        return None

    def toggle_pause(self):
        if self.executable is not None:
            self.paused = not self.paused
            self.update_lock()

    def handle_tray_action(self, action: str):
        if action == "settings":
            self.show_panel()
        elif action == "exit":
            self.close()
            self.root.quit()
        elif action == "toggle":
            self.toggle_pause()

    def update_lock(self):
        if self.executable is None:
            self.cursor.release()
            status = "Choose a game"
        elif self.paused:
            self.cursor.release()
            status = "Paused"
        else:
            status = self.cursor.update(self.executable)

        self.tray.update(status, self.paused, self.executable is not None)
        if self.panel_visible:
            now = monotonic()
            if now >= self.next_display_check:
                self.displays = connected_displays()
                self.next_display_check = now + 1.0
            self.panel.refresh(status, self.executable, self.paused, self.displays, self.cursor.game_monitor)

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
