"""Tiện ích X11/XWayland EWMH để ẩn widget khỏi Taskbar/Pager và đặt lớp hiển thị trên KWin."""

from __future__ import annotations

import ctypes
from ctypes import byref, c_int, c_long, c_ubyte, c_uint, c_ulong, c_void_p

from PyQt6.QtGui import QGuiApplication


class _XClientMessageData(ctypes.Union):
    _fields_ = [("b", ctypes.c_char * 20), ("s", ctypes.c_short * 10), ("l", c_long * 5)]


class _XClientMessageEvent(ctypes.Structure):
    _fields_ = [
        ("type", c_int),
        ("serial", c_ulong),
        ("send_event", c_int),
        ("display", c_void_p),
        ("window", c_ulong),
        ("message_type", c_ulong),
        ("format", c_int),
        ("data", _XClientMessageData),
    ]


_LIBX11 = None


def _get_x11():
    global _LIBX11
    if _LIBX11 is not None:
        return _LIBX11
    try:
        lib = ctypes.cdll.LoadLibrary("libX11.so.6")
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XOpenDisplay.restype = c_void_p
        lib.XCloseDisplay.argtypes = [c_void_p]
        lib.XCloseDisplay.restype = c_int
        lib.XDefaultRootWindow.argtypes = [c_void_p]
        lib.XDefaultRootWindow.restype = c_ulong
        lib.XInternAtom.argtypes = [c_void_p, ctypes.c_char_p, c_int]
        lib.XInternAtom.restype = c_ulong
        lib.XChangeProperty.argtypes = [
            c_void_p,
            c_ulong,
            c_ulong,
            c_ulong,
            c_int,
            c_int,
            ctypes.POINTER(c_ubyte),
            c_int,
        ]
        lib.XChangeProperty.restype = c_int
        lib.XSendEvent.argtypes = [c_void_p, c_ulong, c_int, c_long, c_void_p]
        lib.XSendEvent.restype = c_int
        lib.XFlush.argtypes = [c_void_p]
        lib.XFlush.restype = c_int
        _LIBX11 = lib
    except OSError:
        _LIBX11 = False
    return _LIBX11


def apply_ewmh_widget_hints(win_id: int, layer: str = "bottom") -> bool:
    """Đặt _NET_WM_STATE_SKIP_TASKBAR, SKIP_PAGER, STICKY và BELOW/ABOVE cho cửa sổ X11/XWayland."""
    if not win_id or QGuiApplication.platformName() != "xcb":
        return False

    x11 = _get_x11()
    if not x11:
        return False

    display = x11.XOpenDisplay(None)
    if not display:
        return False

    try:
        root = x11.XDefaultRootWindow(display)
        wm_state = x11.XInternAtom(display, b"_NET_WM_STATE", 0)
        xa_atom = 4  # XA_ATOM
        prop_mode_replace = 0

        atom_names = [
            b"_NET_WM_STATE_SKIP_TASKBAR",
            b"_NET_WM_STATE_SKIP_PAGER",
            b"_NET_WM_STATE_STICKY",
        ]
        if layer == "bottom":
            atom_names.append(b"_NET_WM_STATE_BELOW")
        elif layer == "top":
            atom_names.append(b"_NET_WM_STATE_ABOVE")

        atoms = [x11.XInternAtom(display, name, 0) for name in atom_names]
        arr = (c_ulong * len(atoms))(*atoms)
        x11.XChangeProperty(
            display,
            c_ulong(win_id),
            wm_state,
            xa_atom,
            32,
            prop_mode_replace,
            ctypes.cast(arr, ctypes.POINTER(c_ubyte)),
            len(atoms),
        )

        # Gửi ClientMessage để Window Manager (KWin) cập nhật ngay cả khi cửa sổ đã map
        substructure_mask = (1 << 20) | (1 << 19)  # SubstructureRedirect | SubstructureNotify
        for i in range(0, len(atoms), 2):
            a1 = atoms[i]
            a2 = atoms[i + 1] if i + 1 < len(atoms) else 0
            ev = _XClientMessageEvent()
            ev.type = 33  # ClientMessage
            ev.send_event = 1
            ev.display = display
            ev.window = c_ulong(win_id)
            ev.message_type = wm_state
            ev.format = 32
            ev.data.l[0] = 1  # _NET_WM_STATE_ADD
            ev.data.l[1] = a1
            ev.data.l[2] = a2
            ev.data.l[3] = 1  # normal application
            ev.data.l[4] = 0
            x11.XSendEvent(display, root, 0, substructure_mask, byref(ev))

        x11.XFlush(display)
        return True
    finally:
        x11.XCloseDisplay(display)
