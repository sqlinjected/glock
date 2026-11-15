"""The glock notification icon and keyboard shortcut on Windows."""

import ctypes as ct
from collections.abc import Callable
from ctypes import wintypes as win
from pathlib import Path


_user32 = ct.WinDLL("user32", use_last_error=True)
_kernel32 = ct.WinDLL("kernel32", use_last_error=True)
_shell32 = ct.WinDLL("shell32", use_last_error=True)

_WINDOW_CLASS = "glock.TrayIcon"
_ICON_ID = 1
_HOTKEY_ID = 1
_WM_TRAY_ICON = 0x8001
_WM_HOTKEY = 0x0312
_WM_CLOSE = 0x0010
_WM_CONTEXTMENU = 0x007B
_WM_LBUTTONDBLCLK = 0x0203
_WM_RBUTTONUP = 0x0205
_NIN_KEYSELECT = 0x0401
_CTRL_ALT_NO_REPEAT = 0x0001 | 0x0002 | 0x4000
_VK_F10 = 0x79

_NIM_ADD = 0
_NIM_MODIFY = 1
_NIM_DELETE = 2
_NIM_SETFOCUS = 3
_NIM_SETVERSION = 4
_NIF_MESSAGE = 0x01
_NIF_ICON = 0x02
_NIF_TIP = 0x04
_NIF_SHOWTIP = 0x80
_NOTIFYICON_VERSION_4 = 4

_MF_STRING = 0x0000
_MF_GRAYED = 0x0001
_MF_SEPARATOR = 0x0800
_TPM_RIGHTBUTTON = 0x0002
_TPM_NONOTIFY = 0x0080
_TPM_RETURNCMD = 0x0100

_SETTINGS = 1
_TOGGLE = 2
_EXIT = 3
_ACTIONS = {_SETTINGS: "settings", _TOGGLE: "toggle", _EXIT: "exit"}


_LRESULT = ct.c_ssize_t
_WNDPROC = ct.WINFUNCTYPE(_LRESULT, win.HWND, win.UINT, win.WPARAM, win.LPARAM)


class _WindowClass(ct.Structure):
    _fields_ = [
        ("style", win.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ct.c_int),
        ("cbWndExtra", ct.c_int),
        ("hInstance", win.HINSTANCE),
        ("hIcon", win.HICON),
        ("hCursor", win.HANDLE),
        ("hbrBackground", win.HBRUSH),
        ("lpszMenuName", win.LPCWSTR),
        ("lpszClassName", win.LPCWSTR),
    ]


class _NotifyIconData(ct.Structure):
    _fields_ = [
        ("cbSize", win.DWORD),
        ("hWnd", win.HWND),
        ("uID", win.UINT),
        ("uFlags", win.UINT),
        ("uCallbackMessage", win.UINT),
        ("hIcon", win.HICON),
        ("szTip", win.WCHAR * 128),
        ("dwState", win.DWORD),
        ("dwStateMask", win.DWORD),
        ("szInfo", win.WCHAR * 256),
        ("uVersion", win.UINT),
        ("szInfoTitle", win.WCHAR * 64),
        ("dwInfoFlags", win.DWORD),
        ("guidItem", win.DWORD * 4),
        ("hBalloonIcon", win.HICON),
    ]


def _bind(dll, name, restype, *argtypes):
    function = getattr(dll, name)
    function.restype = restype
    function.argtypes = argtypes
    return function


_get_module = _bind(_kernel32, "GetModuleHandleW", win.HMODULE, win.LPCWSTR)
_register_class = _bind(_user32, "RegisterClassW", win.ATOM, ct.POINTER(_WindowClass))
_unregister_class = _bind(_user32, "UnregisterClassW", win.BOOL, win.LPCWSTR, win.HINSTANCE)
_create_window = _bind(
    _user32, "CreateWindowExW", win.HWND,
    win.DWORD, win.LPCWSTR, win.LPCWSTR, win.DWORD, ct.c_int, ct.c_int, ct.c_int, ct.c_int,
    win.HWND, win.HMENU, win.HINSTANCE, win.LPVOID,
)
_destroy_window = _bind(_user32, "DestroyWindow", win.BOOL, win.HWND)
_default_proc = _bind(_user32, "DefWindowProcW", _LRESULT, win.HWND, win.UINT, win.WPARAM, win.LPARAM)
_register_message = _bind(_user32, "RegisterWindowMessageW", win.UINT, win.LPCWSTR)
_register_hotkey = _bind(_user32, "RegisterHotKey", win.BOOL, win.HWND, ct.c_int, win.UINT, win.UINT)
_unregister_hotkey = _bind(_user32, "UnregisterHotKey", win.BOOL, win.HWND, ct.c_int)
_get_metric = _bind(_user32, "GetSystemMetrics", ct.c_int, ct.c_int)
_load_image = _bind(
    _user32, "LoadImageW", win.HANDLE, win.HINSTANCE, win.LPCWSTR, win.UINT, ct.c_int, ct.c_int, win.UINT,
)
_destroy_icon = _bind(_user32, "DestroyIcon", win.BOOL, win.HICON)
_notify_icon = _bind(_shell32, "Shell_NotifyIconW", win.BOOL, win.DWORD, ct.POINTER(_NotifyIconData))
_create_menu = _bind(_user32, "CreatePopupMenu", win.HMENU)
_destroy_menu = _bind(_user32, "DestroyMenu", win.BOOL, win.HMENU)
_append_menu = _bind(_user32, "AppendMenuW", win.BOOL, win.HMENU, win.UINT, ct.c_size_t, win.LPCWSTR)
_track_menu = _bind(
    _user32, "TrackPopupMenu", win.BOOL,
    win.HMENU, win.UINT, ct.c_int, ct.c_int, ct.c_int, win.HWND, ct.POINTER(win.RECT),
)
_get_cursor = _bind(_user32, "GetCursorPos", win.BOOL, ct.POINTER(win.POINT))
_set_foreground = _bind(_user32, "SetForegroundWindow", win.BOOL, win.HWND)
_post_message = _bind(_user32, "PostMessageW", win.BOOL, win.HWND, win.UINT, win.WPARAM, win.LPARAM)


class TrayIcon:
    """Manage the icon on the main thread. The callback should only enqueue actions."""

    def __init__(self, icon_path: Path, on_action: Callable[[str], None]) -> None:
        self._on_action = on_action
        self._status = "Starting"
        self._paused = False
        self._can_pause = False
        self._started = False
        self._visible = False
        self._version_4 = False
        self._hwnd = None
        self._icon = None
        self._class_atom = 0
        self.hotkey_registered = False
        self._module = _get_module(None)
        self._taskbar_created = _register_message("TaskbarCreated")
        # Keep the callback alive for as long as Windows can call it.
        self._callback = _WNDPROC(self._window_proc)

        try:
            window_class = _WindowClass(
                lpfnWndProc=self._callback, hInstance=self._module, lpszClassName=_WINDOW_CLASS,
            )
            self._class_atom = _register_class(ct.byref(window_class))
            if not self._class_atom:
                raise ct.WinError(ct.get_last_error())

            # A hidden top-level window can receive Explorer's restart broadcast.
            self._hwnd = _create_window(
                0, _WINDOW_CLASS, "glock", 0, 0, 0, 0, 0, None, None, self._module, None,
            )
            if not self._hwnd:
                raise ct.WinError(ct.get_last_error())

            image_icon, load_from_file = 1, 0x0010
            small_icon_width, small_icon_height = 49, 50
            self._icon = _load_image(
                None, str(icon_path), image_icon, _get_metric(small_icon_width),
                _get_metric(small_icon_height), load_from_file,
            )
            if not self._icon:
                raise ct.WinError(ct.get_last_error())

            self.hotkey_registered = bool(
                _register_hotkey(self._hwnd, _HOTKEY_ID, _CTRL_ALT_NO_REPEAT, _VK_F10)
            )
        except BaseException:
            self.close()
            raise

    def start(self) -> None:
        if self._started:
            return
        if not self._add_icon():
            raise OSError("Could not add glock to the Windows notification area.")
        self._started = True

    def update(self, status: str, paused: bool, can_pause: bool) -> None:
        self._paused = paused
        self._can_pause = can_pause
        if status != self._status:
            self._status = status
            if self._visible:
                self._notify(_NIM_MODIFY, _NIF_TIP | _NIF_SHOWTIP)

    def close(self) -> None:
        self._started = False
        if self._visible:
            self._notify(_NIM_DELETE)
            self._visible = False
        if self.hotkey_registered:
            _unregister_hotkey(self._hwnd, _HOTKEY_ID)
            self.hotkey_registered = False
        if self._hwnd:
            _destroy_window(self._hwnd)
            self._hwnd = None
        if self._class_atom:
            _unregister_class(_WINDOW_CLASS, self._module)
            self._class_atom = 0
        if self._icon:
            _destroy_icon(self._icon)
            self._icon = None

    def _notify(self, message: int, flags: int = 0) -> bool:
        data = _NotifyIconData(
            cbSize=ct.sizeof(_NotifyIconData), hWnd=self._hwnd, uID=_ICON_ID, uFlags=flags,
            uCallbackMessage=_WM_TRAY_ICON, hIcon=self._icon, szTip=f"glock • {self._status}",
            uVersion=_NOTIFYICON_VERSION_4,
        )
        return bool(_notify_icon(message, ct.byref(data)))

    def _add_icon(self) -> bool:
        self._visible = self._notify(_NIM_ADD, _NIF_ICON | _NIF_MESSAGE | _NIF_TIP | _NIF_SHOWTIP)
        if self._visible:
            self._version_4 = self._notify(_NIM_SETVERSION)
        return self._visible

    def _window_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == _WM_TRAY_ICON:
            event = lparam & 0xFFFF
            menu_event = _WM_CONTEXTMENU if self._version_4 else _WM_RBUTTONUP
            if event == menu_event:
                self._show_menu()
            elif event in (_WM_LBUTTONDBLCLK, _NIN_KEYSELECT):
                self._on_action("settings")
            return 0
        if message == _WM_HOTKEY and wparam == _HOTKEY_ID:
            self._on_action("toggle")
            return 0
        if message == _WM_CLOSE:
            self._on_action("exit")
            return 0
        if message == self._taskbar_created and message and self._started:
            self._add_icon()
            return 0
        return _default_proc(hwnd, message, wparam, lparam)

    def _show_menu(self) -> None:
        position = win.POINT()
        if not _get_cursor(ct.byref(position)):
            return
        menu = _create_menu()
        if not menu:
            return
        try:
            _append_menu(menu, _MF_STRING | _MF_GRAYED, 0, self._status)
            _append_menu(menu, _MF_SEPARATOR, 0, None)
            _append_menu(menu, _MF_STRING, _SETTINGS, "Settings")

            pause_label = "Resume" if self._paused else "Pause"
            if self.hotkey_registered:
                pause_label += "\tCtrl+Alt+F10"
            pause_flags = _MF_STRING if self._can_pause else _MF_STRING | _MF_GRAYED
            _append_menu(menu, pause_flags, _TOGGLE, pause_label)
            _append_menu(menu, _MF_STRING, _EXIT, "Exit")

            _set_foreground(self._hwnd)
            command = _track_menu(
                menu, _TPM_RIGHTBUTTON | _TPM_NONOTIFY | _TPM_RETURNCMD,
                position.x, position.y, 0, self._hwnd, None,
            )
            # Let a click outside the menu dismiss it and allow it to open again.
            _post_message(self._hwnd, 0, 0, 0)
        finally:
            _destroy_menu(menu)

        if command in _ACTIONS:
            self._on_action(_ACTIONS[command])
        elif not command:
            self._notify(_NIM_SETFOCUS)
