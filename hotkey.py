"""Pause shortcut choices shared by the panel and the Windows tray."""

from dataclasses import dataclass
from string import ascii_uppercase, digits


FUNCTION_KEYS = tuple(f"F{number}" for number in range(1, 25) if number != 12)
KEYS = tuple(ascii_uppercase + digits) + FUNCTION_KEYS
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000


@dataclass(frozen=True)
class Hotkey:
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False

    def __post_init__(self):
        key = self.key.strip().upper()
        if key not in KEYS:
            raise ValueError("Choose a letter, number, or function key other than F12.")
        if key not in FUNCTION_KEYS and not (self.ctrl or self.alt or self.shift):
            raise ValueError("Add Ctrl, Alt, or Shift to use a letter or number.")
        object.__setattr__(self, "key", key)

    @property
    def label(self) -> str:
        parts = [label for label, selected in (("Ctrl", self.ctrl), ("Alt", self.alt), ("Shift", self.shift)) if selected]
        return "+".join([*parts, self.key])

    @property
    def modifiers(self) -> int:
        return MOD_NOREPEAT | sum(
            flag for flag, selected in ((MOD_CONTROL, self.ctrl), (MOD_ALT, self.alt), (MOD_SHIFT, self.shift)) if selected
        )

    @property
    def virtual_key(self) -> int:
        if self.key in FUNCTION_KEYS:
            return 0x70 + int(self.key[1:]) - 1
        return ord(self.key)


DEFAULT_HOTKEY = Hotkey("F10", ctrl=True, alt=True)


def parse_hotkey(text: str) -> Hotkey:
    *modifiers, key = (part.strip().lower() for part in text.split("+"))
    selected = set(modifiers)
    if selected - {"ctrl", "alt", "shift"} or len(selected) != len(modifiers):
        raise ValueError("Use Ctrl, Alt, or Shift as shortcut modifiers.")
    return Hotkey(key, ctrl="ctrl" in selected, alt="alt" in selected, shift="shift" in selected)
