"""The boomchikaUI window and live display map."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from cursor_lock import Bounds, Display


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
    def __init__(self, master, logo_path: Path, hotkey: bool, save_game, toggle_pause):
        super().__init__(master, background=WINDOW)
        self.save_game = save_game
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
        if hotkey:
            keys = tk.Frame(footer, background=BAR)
            keys.pack(side="right", padx=(8, 0))
            self.label(keys, "Pause", 9, color=MUTED, background=BAR).pack(side="left", padx=(0, 7))
            for key in ("Ctrl", "Alt", "F10"):
                self.label(keys, key, 9, background=BUTTON, padx=5, pady=1).pack(side="left", padx=(0, 3))

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
