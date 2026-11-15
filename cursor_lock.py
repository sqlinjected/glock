"""Windows display geometry, cursor confinement, and single-instance support."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import ntpath


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_ERROR_ALREADY_EXISTS = 183
_CSTR_EQUAL = 2
_MONITOR_DEFAULTTONULL = 0
_MONITORINFOF_PRIMARY = 1
_PER_MONITOR_AWARE = -3
_PER_MONITOR_AWARE_V2 = -4

Bounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class Display:
    name: str
    bounds: Bounds
    primary: bool


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("monitor", wintypes.RECT),
        ("work_area", wintypes.RECT),
        ("flags", wintypes.DWORD),
        ("device_name", wintypes.WCHAR * 32),
    ]


_MonitorCallback = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, wintypes.LPRECT, wintypes.LPARAM,
)


def _bind(dll, name, result, *arguments):
    function = getattr(dll, name)
    function.restype = result
    function.argtypes = arguments
    return function


_get_foreground_window = _bind(_user32, "GetForegroundWindow", wintypes.HWND)
_get_window_process = _bind(
    _user32, "GetWindowThreadProcessId", wintypes.DWORD, wintypes.HWND, wintypes.LPDWORD
)
_get_window_monitor = _bind(
    _user32, "MonitorFromWindow", wintypes.HMONITOR, wintypes.HWND, wintypes.DWORD
)
_get_monitor_info = _bind(
    _user32, "GetMonitorInfoW", wintypes.BOOL, wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo)
)
_enum_display_monitors = _bind(
    _user32, "EnumDisplayMonitors", wintypes.BOOL,
    wintypes.HDC, wintypes.LPRECT, _MonitorCallback, wintypes.LPARAM,
)
_get_clip = _bind(_user32, "GetClipCursor", wintypes.BOOL, wintypes.LPRECT)
_set_clip = _bind(_user32, "ClipCursor", wintypes.BOOL, wintypes.LPRECT)
_open_process = _bind(
    _kernel32, "OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
)
_get_image_name = _bind(
    _kernel32, "QueryFullProcessImageNameW", wintypes.BOOL,
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, wintypes.LPDWORD,
)
_compare_name = _bind(
    _kernel32, "CompareStringOrdinal", ctypes.c_int,
    wintypes.LPCWSTR, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int, wintypes.BOOL,
)
_create_mutex = _bind(
    _kernel32, "CreateMutexW", wintypes.HANDLE, wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR
)
_release_mutex = _bind(_kernel32, "ReleaseMutex", wintypes.BOOL, wintypes.HANDLE)
_close_handle = _bind(_kernel32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)


def enable_dpi_awareness() -> None:
    """Use physical screen coordinates before any windows are created."""
    try:
        set_process_context = _bind(
            _user32, "SetProcessDpiAwarenessContext", wintypes.BOOL, wintypes.HANDLE
        )
        set_thread_context = _bind(
            _user32, "SetThreadDpiAwarenessContext", wintypes.HANDLE, wintypes.HANDLE
        )
    except AttributeError:
        shcore = ctypes.WinDLL("shcore")
        set_process_awareness = _bind(shcore, "SetProcessDpiAwareness", ctypes.c_long, ctypes.c_int)
        set_process_awareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return

    for context in (_PER_MONITOR_AWARE_V2, _PER_MONITOR_AWARE):
        if set_process_context(context) or set_thread_context(context):
            return


class SingleInstance:
    """Keep one copy per desktop session, including the older Windows build."""

    def __enter__(self) -> bool:
        ctypes.set_last_error(0)
        self._handle = _create_mutex(None, True, r"Local\GameCursorLock")
        error = ctypes.get_last_error()
        if not self._handle:
            raise ctypes.WinError(error)
        self._owned = error != _ERROR_ALREADY_EXISTS
        return self._owned

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._owned:
            _release_mutex(self._handle)
        _close_handle(self._handle)


def _read_executable_name(pid: int) -> str | None:
    process = _open_process(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process:
        return None

    try:
        path = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(path))
        if _get_image_name(process, 0, path, ctypes.byref(size)):
            return ntpath.basename(path.value)
        return None
    finally:
        _close_handle(process)


def _bounds(rect: wintypes.RECT) -> Bounds:
    return (rect.left, rect.top, rect.right, rect.bottom)


def _monitor_info(monitor: int | None) -> _MonitorInfo | None:
    if not monitor:
        return None

    info = _MonitorInfo(size=ctypes.sizeof(_MonitorInfo))
    if not _get_monitor_info(monitor, ctypes.byref(info)):
        return None

    rect = info.monitor
    return info if rect.left < rect.right and rect.top < rect.bottom else None


def _monitor_bounds(window: int) -> Bounds | None:
    info = _monitor_info(_get_window_monitor(window, _MONITOR_DEFAULTTONULL))
    return _bounds(info.monitor) if info is not None else None


def connected_displays() -> tuple[Display, ...]:
    """Return each desktop display area in physical pixels, primary first."""
    displays: dict[Bounds, Display] = {}

    @_MonitorCallback
    def add_display(monitor, _device_context, _rect, _data):
        info = _monitor_info(monitor)
        if info is not None:
            bounds = _bounds(info.monitor)
            primary = bool(info.flags & _MONITORINFOF_PRIMARY)
            # Mirrored displays can refer to the same desktop area.
            if bounds not in displays or primary:
                device = info.device_name.removeprefix("\\\\.\\")
                number = device.upper().removeprefix("DISPLAY")
                name = f"Display {number}" if number.isdecimal() else device or "Display"
                displays[bounds] = Display(name, bounds, primary)
        return True

    if not _enum_display_monitors(None, None, add_display, 0):
        return ()
    return tuple(sorted(displays.values(), key=lambda display: (not display.primary, display.bounds)))


def _read_clip() -> Bounds | None:
    rect = wintypes.RECT()
    if _get_clip(ctypes.byref(rect)):
        return _bounds(rect)
    return None


def _contains(outer: Bounds, inner: Bounds) -> bool:
    return (
        outer[0] <= inner[0] and outer[1] <= inner[1]
        and outer[2] >= inner[2] and outer[3] >= inner[3]
    )


class CursorLock:
    def __init__(self) -> None:
        self._focused_process: tuple[int, int] | None = None
        self._focused_exe: str | None = None
        self._applied_clip: Bounds | None = None
        self._game_monitor: Bounds | None = None

    @property
    def game_monitor(self) -> Bounds | None:
        return self._game_monitor

    def _focused_game(self, executable: str) -> int | None:
        window = _get_foreground_window()
        pid = wintypes.DWORD()
        if not window or not _get_window_process(window, ctypes.byref(pid)):
            self._focused_process = None
            self._focused_exe = None
            return None

        focused_process = (window, pid.value)
        if focused_process != self._focused_process:
            self._focused_process = focused_process
            self._focused_exe = _read_executable_name(pid.value)

        if self._focused_exe and _compare_name(
            self._focused_exe, -1, executable, -1, True,
        ) == _CSTR_EQUAL:
            return window
        return None

    def update(self, executable: str) -> str:
        game = self._focused_game(executable)
        if game is None:
            self.release()
            return "Waiting for game focus"

        monitor = _monitor_bounds(game)
        current = _read_clip()
        if monitor is None or _get_foreground_window() != game:
            self.release()
            return "Could not lock cursor"

        self._game_monitor = monitor
        if current is None:
            self._release_clip()
            return "Could not lock cursor"

        if current != self._applied_clip:
            self._applied_clip = None
            # A game may set a smaller clip for its camera or menus.
            if _contains(monitor, current):
                return "Cursor locked"

        if current == monitor:
            return "Cursor locked"

        if _set_clip(ctypes.byref(wintypes.RECT(*monitor))):
            self._applied_clip = monitor
            return "Cursor locked"

        self._release_clip()
        return "Could not lock cursor"

    def release(self) -> None:
        self._game_monitor = None
        self._release_clip()

    def _release_clip(self) -> None:
        if self._applied_clip is None:
            return

        current = _read_clip()
        if current is not None and (current != self._applied_clip or _set_clip(None)):
            self._applied_clip = None
