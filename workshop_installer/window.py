"""One native Windows Setup window with named buttons; no GUI runtime dependency."""
import ctypes
import os
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
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wt.DWORD] * 8 + [wt.LPCWSTR]
gdi32.CreateFontW.restype = wt.HFONT
gdi32.DeleteObject.argtypes = [wt.HANDLE]


class Window:
    def __init__(self, title):
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

    def _control(self, kind, text, style, x, y, width, height, number=0, heading=False):
        h = user32.CreateWindowExW(0, kind, text, 0x50000000 | style, self.px(x), self.px(y),
                                   self.px(width), self.px(height), self.hwnd, wt.HMENU(number), self.instance, None)
        if not h:
            raise ctypes.WinError(ctypes.get_last_error())
        user32.SendMessageW(h, 0x30, self.heading_font if heading else self.font, 1)
        self.children.append(h)
        return h

    def page(self, title, subtitle, message, buttons):
        self.actions.clear()
        for h in self.children:
            user32.DestroyWindow(h)
        self.children.clear()
        self.buttons.clear()
        self.details_handle = None
        user32.SetWindowPos(self.hwnd, None, 0, 0, self.px(650), self.px(490), 0x16)
        self._control("STATIC", title, 0x80, 24, 20, 590, 34, heading=True)
        self._control("STATIC", subtitle, 0x80, 24, 64, 590, 66)
        self._control("STATIC", message, 0x80, 24, 142, 590, 240)
        x = 610
        for i, (label, callback) in reversed(list(enumerate(buttons, 100))):
            width = max(80, len(label) * 8 + 20)
            x -= width
            self.buttons.append(self._control("BUTTON", label, 0x10000, x, 405, width, 32, i))
            self.actions[i] = callback
            x -= 10
        user32.UpdateWindow(self.hwnd)

    def details(self, text):
        if self.details_handle:
            return
        user32.SetWindowPos(self.hwnd, None, 0, 0, self.px(650), self.px(670), 0x16)
        self.details_handle = self._control("EDIT", text, 0x00200844 | 0x800000, 24, 452, 590, 150)

    def set_busy(self, busy):
        self.busy = busy
        for h in self.buttons:
            user32.EnableWindow(h, not busy)
        user32.UpdateWindow(self.hwnd)

    def _message(self, hwnd, msg, wp, lp):
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
                user32.DestroyWindow(hwnd)
            return 0
        if msg == 2:  # WM_DESTROY
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def close(self):
        if not self.busy:
            user32.DestroyWindow(self.hwnd)

    def dispose(self):
        user32.DestroyWindow(self.hwnd)
        user32.UnregisterClassW(self.classname, self.instance)
        gdi32.DeleteObject(self.font)
        gdi32.DeleteObject(self.heading_font)

    def run(self):
        user32.ShowWindow(self.hwnd, 5)
        message = wt.MSG()
        try:
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
