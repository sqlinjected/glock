"""The boomchikaUI window and live display map."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from cursor_lock import Bounds, Display
from hotkey import Hotkey


WINDOW = "#201e21"
BAR = "#282529"
SCREEN = "#2b282c"
BORDER = "#484149"
TEXT = "#f6eee3"
MUTED = "#c1b3a9"
AMBER = "#ffc571"
AMBER_EDGE = "#e8a747"
AMBER_SURFACE = "#423223"
BUTTON = "#342f35"
FONT = "Segoe UI"


class BoomchikaPanel(tk.Frame):
    def __init__(self, master, logo_path: Path, hotkey: Hotkey, hotkey_registered: bool,
                 save_game, toggle_pause, change_hotkey):
        super().__init__(master, background=WINDOW)
        self.save_game = save_game
        self.change_hotkey = change_hotkey
        self.shortcut_editor: tk.Toplevel | None = None
        self.displays: tuple[Display, ...] = ()
        self.game_monitor: Bounds | None = None
        self.game_name = ""
        self.view = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = tk.Frame(self, background=BAR, padx=20, pady=14)
        header.grid(row=0, column=0, sticky="ew")
        self.logo = tk.PhotoImage(master=header, file=str(logo_path)).subsample(2)
        tk.Label(header, image=self.logo, background=BAR).grid(row=0, column=0, rowspan=2, padx=(0, 11))
        self.label(header, "boomchikaUI", 17, bold=True, background=BAR).grid(row=0, column=1, sticky="w")
        self.label(header, "glock", 9, color=MUTED, background=BAR).grid(row=1, column=1, sticky="w")
        tk.Frame(self, background=BORDER, height=1).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(self, background=WINDOW, padx=20, pady=17)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        self.status = self.label(body, "Choose a game", 16, bold=True)
        self.status.grid(row=0, column=0, sticky="w")
        self.status_detail = self.label(body, "", 10, color=MUTED)
        self.status_detail.grid(row=1, column=0, sticky="ew")
        self.pause_button = self.button(body, "Pause lock", toggle_pause)
        self.pause_button.configure(width=12, state="disabled")
        self.pause_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

        self.label(body, "Connected displays", 10, color=MUTED).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(18, 6)
        )
        self.map = tk.Canvas(body, width=480, height=147, background=WINDOW, highlightthickness=0)
        self.map.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.map.bind("<Configure>", lambda _event: self.draw_displays())

        game = tk.Frame(body, background=WINDOW)
        game.columnconfigure(0, weight=1)
        game.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.label(game, "Game executable", 10, color=MUTED).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.executable = tk.StringVar(master=self)
        self.entry = tk.Entry(
            game, textvariable=self.executable, font=("Consolas", 10), background=SCREEN,
            foreground=TEXT, insertbackground=AMBER, selectbackground=AMBER_SURFACE,
            selectforeground=TEXT, relief="flat", highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=AMBER_EDGE,
        )
        self.entry.grid(row=1, column=0, sticky="ew", ipady=6)
        self.entry.bind("<Return>", lambda _event: self.save_game(self.executable.get()))
        self.button(game, "Browse…", self.browse).grid(row=1, column=1, padx=(8, 0), sticky="ns")
        self.apply_button = self.button(game, "Start", lambda: self.save_game(self.executable.get()), primary=True)
        self.apply_button.configure(width=6)
        self.apply_button.grid(row=1, column=2, sticky="ns", padx=(8, 0))

        tk.Frame(self, background=BORDER, height=1).grid(row=3, column=0, sticky="ew")
        footer = tk.Frame(self, background=BAR, padx=20, pady=9)
        footer.grid(row=4, column=0, sticky="ew")
        self.label(footer, "Alt+Tab frees the mouse", 9, color=MUTED, background=BAR).pack(side="left")
        keys = tk.Frame(footer, background=BAR)
        keys.pack(side="right", padx=(8, 0))
        self.label(keys, "Pause shortcut", 9, color=MUTED, background=BAR).pack(side="left", padx=(0, 7))
        self.shortcut_display = self.label(keys, "", 9, background=BUTTON, padx=5, pady=1)
        self.shortcut_display.pack(side="left", padx=(0, 6))
        self.shortcut_button = self.button(keys, "Change", self.edit_shortcut)
        self.shortcut_button.configure(font=(FONT, 9, "bold"), padx=7, pady=2)
        self.shortcut_button.pack(side="left")
        self.set_hotkey(hotkey, hotkey_registered)

    @staticmethod
    def label(master, text, size, *, bold=False, color=TEXT, background=WINDOW, **kwargs):
        return tk.Label(
            master, text=text, foreground=color, background=background,
            font=(FONT, size, "bold" if bold else "normal"), highlightthickness=0, anchor="w", **kwargs,
        )

    @staticmethod
    def button(master, text, command, *, primary=False):
        return tk.Button(
            master, text=text, command=command, font=(FONT, 10, "bold"), relief="flat",
            background=AMBER if primary else BUTTON, foreground="#261a0f" if primary else TEXT,
            activebackground="#ffd59a" if primary else AMBER_SURFACE,
            activeforeground="#261a0f" if primary else TEXT, disabledforeground=MUTED,
            padx=10, pady=5, borderwidth=0, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=AMBER_EDGE, takefocus=True,
        )

    def edit_game(self, executable: str, *, focus: bool = False):
        self.executable.set(executable)
        if focus:
            self.entry.focus_set()
            self.entry.selection_range(0, tk.END)

    def browse(self):
        path = filedialog.askopenfilename(
            parent=self, title="Choose your game", filetypes=[("Windows executables", "*.exe")]
        )
        if path:
            self.edit_game(Path(path).name)

    def set_hotkey(self, hotkey: Hotkey, registered: bool):
        self.hotkey = hotkey
        label = hotkey.label if registered else f"{hotkey.label} (unavailable)"
        self.shortcut_display.configure(text=label, foreground=TEXT if registered else AMBER)

    def edit_shortcut(self):
        if self.shortcut_editor is not None:
            self.shortcut_editor.lift()
            return

        dialog = tk.Toplevel(self)
        self.shortcut_editor = dialog
        dialog.title("Pause shortcut")
        dialog.transient(self.winfo_toplevel())
        dialog.resizable(False, False)
        content = tk.Frame(dialog, background=WINDOW, padx=20, pady=16)
        content.pack(fill="both", expand=True)

        self.label(content, "Key", 10, bold=True).grid(row=0, column=0, sticky="w", pady=(0, 5))
        key = tk.StringVar(master=dialog, value=self.hotkey.key)
        entry = tk.Entry(
            content, textvariable=key, width=8, font=("Consolas", 11), background=SCREEN,
            foreground=TEXT, insertbackground=AMBER, selectbackground=AMBER_SURFACE,
            selectforeground=TEXT, relief="flat", highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=AMBER_EDGE,
        )
        entry.grid(row=1, column=0, sticky="w", ipady=4)
        self.label(content, "Type a key like L or F8.", 9, color=MUTED).grid(
            row=1, column=1, sticky="w", padx=(10, 0)
        )

        modifiers = tk.Frame(content, background=WINDOW)
        modifiers.grid(row=2, column=0, columnspan=2, sticky="w", pady=(11, 0))
        ctrl = tk.BooleanVar(master=dialog, value=self.hotkey.ctrl)
        alt = tk.BooleanVar(master=dialog, value=self.hotkey.alt)
        shift = tk.BooleanVar(master=dialog, value=self.hotkey.shift)
        for label, variable in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)):
            tk.Checkbutton(
                modifiers, text=label, variable=variable, font=(FONT, 10), background=WINDOW,
                foreground=TEXT, activebackground=WINDOW, activeforeground=TEXT, selectcolor=AMBER_EDGE,
                highlightthickness=1, highlightbackground=WINDOW, highlightcolor=AMBER_EDGE,
            ).pack(side="left", padx=(0, 10))

        error_label = self.label(content, "", 9, color=AMBER, wraplength=270, justify="left")
        error_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 12))

        def close():
            self.shortcut_editor = None
            dialog.destroy()
            self.shortcut_button.focus_set()

        def apply():
            try:
                hotkey = Hotkey(key.get(), ctrl.get(), alt.get(), shift.get())
            except ValueError as error:
                error_label.configure(text=str(error))
                return

            error = self.change_hotkey(hotkey)
            if error:
                error_label.configure(text=error)
            else:
                close()

        actions = tk.Frame(content, background=WINDOW)
        actions.grid(row=4, column=0, columnspan=2, sticky="e")
        self.button(actions, "Cancel", close).pack(side="left", padx=(0, 6))
        self.button(actions, "Save", apply, primary=True).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.bind("<Escape>", lambda _event: close())
        entry.bind("<Return>", lambda _event: apply())
        dialog.grab_set()
        entry.focus_set()
        entry.selection_range(0, tk.END)

    def refresh(self, status, executable, paused, displays, game_monitor):
        view = (status, executable, paused, displays, game_monitor)
        if view == self.view:
            return
        self.view = view
        game_name = "LEGO Universe" if (executable or "").lower() == "legouniverse.exe" else (executable or "")
        display_name = next((display.name for display in displays if display.bounds == game_monitor), None)
        locked = status == "Cursor locked"

        title = status
        detail = game_name or "Pick the game you want to keep the mouse in."
        if status == "Waiting for game focus":
            title = "Waiting for game"
        elif status == "Paused":
            title = "Lock paused"
        if display_name and game_name:
            detail = f"{game_name} on {display_name}"

        if len(detail) > 43:
            detail = detail[:40] + "…"
        self.status.configure(text=title, foreground=AMBER if locked else TEXT)
        self.status_detail.configure(text=detail)
        self.pause_button.configure(text="Resume lock" if paused else "Pause lock",
                                    state="normal" if executable else "disabled")
        self.apply_button.configure(text="Apply" if executable else "Start")

        highlighted = game_monitor if locked else None
        if (displays, highlighted, game_name) != (self.displays, self.game_monitor, self.game_name):
            self.displays = displays
            self.game_monitor = highlighted
            self.game_name = game_name
            self.draw_displays()

    def draw_displays(self):
        self.map.delete("all")
        width, height = self.map.winfo_width(), self.map.winfo_height()
        if width < 20 or height < 20:
            return
        if not self.displays:
            self.map.create_text(width / 2, height / 2, text="No displays detected", fill=MUTED, font=(FONT, 10))
            return

        left = min(display.bounds[0] for display in self.displays)
        top = min(display.bounds[1] for display in self.displays)
        desktop_width = max(display.bounds[2] for display in self.displays) - left
        desktop_height = max(display.bounds[3] for display in self.displays) - top
        scale = min((width - 6) / desktop_width, (height - 6) / desktop_height)
        center_x = (width - desktop_width * scale) / 2
        center_y = (height - desktop_height * scale) / 2

        for display in self.displays:
            x1, y1, x2, y2 = display.bounds
            x = center_x + (x1 - left) * scale
            y = center_y + (y1 - top) * scale
            screen_width = (x2 - x1) * scale
            screen_height = (y2 - y1) * scale
            inset = min(3, screen_width / 5, screen_height / 5)
            active = display.bounds == self.game_monitor
            self.map.create_rectangle(
                x + inset, y + inset, x + screen_width - inset, y + screen_height - inset,
                fill=AMBER_SURFACE if active else SCREEN, outline=AMBER_EDGE if active else BORDER, width=2,
            )
            self.draw_display_label(display, x, y, screen_width, screen_height, active)

    def draw_display_label(self, display, x, y, width, height, active):
        if width < 33 or height < 24:
            return
        title = display.name if width >= 66 else display.name.removeprefix("Display ")
        subtitle = self.game_name if active else "Primary" if display.primary else ""
        center_x, center_y = x + width / 2, y + height / 2
        if height >= 48 and width >= 76 and subtitle:
            limit = max(7, int((width - 14) / 6.5))
            if len(subtitle) > limit:
                subtitle = subtitle[:limit - 1] + "…"
            self.map.create_text(center_x, center_y + 10, text=subtitle, fill=AMBER if active else MUTED,
                                 font=(FONT, 9))
            center_y -= 7
        self.map.create_text(center_x, center_y, text=title, fill=TEXT, font=(FONT, 10, "bold"))
