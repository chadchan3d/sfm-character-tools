"""One native Windows Setup window with named buttons; no GUI runtime dependency."""
import ctypes
import os
import threading
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR)]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wt.ATOM
user32.UnregisterClassW.argtypes = [wt.LPCWSTR, wt.HINSTANCE]
user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU,
                                 wt.HINSTANCE, wt.LPVOID]
user32.CreateWindowExW.restype = wt.HWND
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = LRESULT
user32.DestroyWindow.argtypes = [wt.HWND]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.UpdateWindow.argtypes = [wt.HWND]
user32.EnableWindow.argtypes = [wt.HWND, wt.BOOL]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.LoadCursorW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadCursorW.restype = wt.HANDLE
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = wt.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.IsDialogMessageW.argtypes = [wt.HWND, ctypes.POINTER(wt.MSG)]
user32.IsDialogMessageW.restype = wt.BOOL
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_size_t, wt.UINT, wt.LPVOID]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wt.HWND, ctypes.c_size_t]
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
user32.DrawTextW.argtypes = [wt.HDC, wt.LPCWSTR, ctypes.c_int, ctypes.POINTER(wt.RECT), wt.UINT]
user32.AdjustWindowRectEx.argtypes = [ctypes.POINTER(wt.RECT), wt.DWORD, wt.BOOL, wt.DWORD]
user32.GetSystemMenu.argtypes = [wt.HWND, wt.BOOL]
user32.GetSystemMenu.restype = wt.HMENU
user32.EnableMenuItem.argtypes = [wt.HMENU, wt.UINT, wt.UINT]
gdi32.SelectObject.argtypes = [wt.HDC, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wt.DWORD] * 8 + [wt.LPCWSTR]
gdi32.CreateFontW.restype = wt.HFONT
gdi32.DeleteObject.argtypes = [wt.HANDLE]


class Window:
    def __init__(self, title):
        self.owner = threading.get_ident()
        self.on_tick = None
        self.on_close = None
        self._disposed = False
        self._next_action = 100
        self._client_width = 616
        self._client_height = 350
        self.busy = False
        self.children = []
        self.buttons = []
        self.actions = {}
        self.details_handle = None
        self.instance = kernel32.GetModuleHandleW(None)
        try:
            user32.SetProcessDPIAware()
        except AttributeError:
            pass
        dpi = user32.GetDpiForSystem() if hasattr(user32, "GetDpiForSystem") else 96
        self.scale = max(1.0, dpi / 96.0)
        self.font = gdi32.CreateFontW(-self.px(15), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI")
        self.metadata_font = gdi32.CreateFontW(-self.px(14), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI")
        self.heading_font = gdi32.CreateFontW(-self.px(21), 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI")
        self.proc = WNDPROC(self._message)  # Keep callback and class alive through window destruction.
        self.classname = "SCT_Setup_%s_%s" % (os.getpid(), id(self))
        self.cls = WNDCLASS(0, self.proc, 0, 0, self.instance, None,
                            user32.LoadCursorW(None, ctypes.cast(32512, wt.LPCWSTR)),
                            wt.HBRUSH(16), None, self.classname)
        if not user32.RegisterClassW(ctypes.byref(self.cls)):
            raise ctypes.WinError(ctypes.get_last_error())
        width, height = self.px(650), self.px(490)
        self.hwnd = user32.CreateWindowExW(0x10000, self.classname, title, 0x00CA0000,
                                           max(0, (user32.GetSystemMetrics(0) - width) // 2),
                                           max(0, (user32.GetSystemMetrics(1) - height) // 2),
                                           width, height, None, None, self.instance, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

    def px(self, value):
        return round(value * self.scale)

    def _owned(self):
        if threading.get_ident() != self.owner:
            raise RuntimeError("Setup controls belong to the UI thread")

    def _height(self, text, width, heading=False, metadata=False):
        if not text:
            return 0
        dc = user32.GetDC(self.hwnd)
        old = gdi32.SelectObject(dc, self.heading_font if heading else self.metadata_font if metadata else self.font)
        try:
            rect = wt.RECT(0, 0, self.px(width), 0)
            # DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX, including long path wrapping.
            user32.DrawTextW(dc, text, len(text), ctypes.byref(rect), 0x400 | 0x10 | 0x800)
            return max(20, round((rect.bottom - rect.top) / self.scale) + 4)
        finally:
            gdi32.SelectObject(dc, old)
            user32.ReleaseDC(self.hwnd, dc)

    def _resize(self, client_height):
        rect = wt.RECT(0, 0, self.px(self._client_width), self.px(client_height))
        user32.AdjustWindowRectEx(ctypes.byref(rect), 0x00CA0000, False, 0x10000)
        user32.SetWindowPos(self.hwnd, None, 0, 0, rect.right - rect.left,
                            rect.bottom - rect.top, 0x16)

    def _control(self, kind, text, style, x, y, width, height, number=0, heading=False, metadata=False):
        self._owned()
        h = user32.CreateWindowExW(0, kind, text, 0x50000000 | style, self.px(x), self.px(y),
                                   self.px(width), self.px(height), self.hwnd, wt.HMENU(number), self.instance, None)
        if not h:
            raise ctypes.WinError(ctypes.get_last_error())
        user32.SendMessageW(h, 0x30, self.heading_font if heading else self.metadata_font if metadata else self.font, 1)
        self.children.append(h)
        return h

    def page(self, title, subtitle, message, buttons):
        self._owned()
        self.actions.clear()
        for h in self.children:
            user32.DestroyWindow(h)
        self.children.clear()
        self.buttons.clear()
        self.details_handle = None
        content_width = self._client_width - 48
        y = 20
        for text, heading, metadata in ((title, True, False), (subtitle, False, True), (message, False, False)):
            if not text:
                continue
            height = self._height(text, content_width, heading, metadata)
            self._control("STATIC", text, 0x80, 24, y, content_width, height,
                          heading=heading, metadata=metadata)
            y += height + (14 if heading else 20)
        self._client_height = max(300, y + 56)
        self._resize(self._client_height)
        x = self._client_width - 24
        numbered = []
        for label, callback in buttons:
            # Never reuse action IDs: queued old clicks cannot invoke a new page's action.
            number = self._next_action
            self._next_action += 1
            numbered.append((number, label, callback))
        for i, label, callback in reversed(numbered):
            width = max(80, len(label) * 8 + 20)
            x -= width
            self.buttons.append(self._control("BUTTON", label, 0x10000, x,
                                              self._client_height - 52, width, 32, i))
            self.actions[i] = callback
            x -= 10
        self.set_busy(self.busy)
        user32.UpdateWindow(self.hwnd)

    def details(self, text):
        self._owned()
        if self.details_handle:
            return
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        self._resize(self._client_height + 164)
        self.details_handle = self._control("EDIT", text, 0x00200844 | 0x800000,
                                            24, self._client_height, self._client_width - 48, 144)

    def set_busy(self, busy):
        self._owned()
        self.busy = busy
        for h in self.buttons:
            user32.EnableWindow(h, not busy)
        menu = user32.GetSystemMenu(self.hwnd, False)
        user32.EnableMenuItem(menu, 0xF060, 1 if busy else 0)  # SC_CLOSE, MF_GRAYED
        user32.UpdateWindow(self.hwnd)

    def _message(self, hwnd, msg, wp, lp):
        if msg == 0x113:  # WM_TIMER: consume worker results on the owning thread.
            if self.on_tick:
                self.on_tick()
            return 0
        if msg == 0x111:  # WM_COMMAND
            action = self.actions.get(wp & 0xFFFF)
            if action and not self.busy:
                try:
                    action()
                except Exception as exc:
                    self.details("Setup could not complete this action.\r\n\r\n" + str(exc))
            return 0
        if msg == 0x10:  # WM_CLOSE
            if not self.busy:
                if self.on_close:
                    self.on_close()
                else:
                    user32.DestroyWindow(hwnd)
            return 0
        if msg == 2:  # WM_DESTROY
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def close(self):
        self._owned()
        if not self.busy:
            user32.DestroyWindow(self.hwnd)

    def dispose(self):
        self._owned()
        if self._disposed:
            return
        self._disposed = True
        user32.KillTimer(self.hwnd, 1)
        user32.DestroyWindow(self.hwnd)
        user32.UnregisterClassW(self.classname, self.instance)
        gdi32.DeleteObject(self.font)
        gdi32.DeleteObject(self.metadata_font)
        gdi32.DeleteObject(self.heading_font)

    def run(self, on_shown=None):
        user32.ShowWindow(self.hwnd, 5)
        # A launcher may supply STARTF_USESHOWWINDOW/SW_HIDE. The first call can
        # honor that startup hint instead of SW_SHOW; Setup still needs a window.
        if not user32.IsWindowVisible(self.hwnd):
            user32.ShowWindow(self.hwnd, 5)
        user32.UpdateWindow(self.hwnd)
        if not user32.SetTimer(self.hwnd, 1, 50, None):
            raise ctypes.WinError(ctypes.get_last_error())
        message = wt.MSG()
        try:
            if on_shown:
                on_shown()
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
                if not user32.IsDialogMessageW(self.hwnd, ctypes.byref(message)):
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
        finally:
            self.dispose()
