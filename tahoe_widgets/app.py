"""Điểm khởi chạy Widget (XWayland positioning + Desktop Widgets + System Tray + i18n)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .drawing import (
    build_symbolic_tray_icon,
    detect_tray_monochrome_color,
    load_bundled_fonts,
)
from .i18n import resolve_language, tr
from .main_window import TahoeControlWindow
from .manager import DesktopWidgetManager
from .settings_store import SettingsStore

SERVER_NAME = "vn.ihoan.TahoeWidgets.ipc"


def _configure_platform_for_positioning() -> None:
    """Ưu tiên XWayland (xcb) nếu có DISPLAY để mỗi widget tự lưu/khôi phục tọa độ (x, y) trên KDE Wayland."""
    if "QT_QPA_PLATFORM" not in os.environ and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def _send_ipc(action: str) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(250):
        socket.write(action.encode("utf-8"))
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    _configure_platform_for_positioning()

    args = argv if argv is not None else sys.argv[1:]
    background_mode = "--background" in args
    want_toggle_panel = "--toggle" in args
    want_toggle_widgets = "--toggle-widgets" in args

    app = QApplication(sys.argv)
    app.setApplicationName("WildOS Widget")
    app.setDesktopFileName("vn.ihoan.TahoeWidgets")

    ipc_cmd = "show"
    if want_toggle_widgets:
        ipc_cmd = "toggle-widgets"
    elif want_toggle_panel:
        ipc_cmd = "toggle-panel"
    elif background_mode:
        ipc_cmd = "sync"

    if _send_ipc(ipc_cmd):
        return 0

    base_dir = Path(__file__).resolve().parent.parent
    assets_dir = base_dir / "assets"
    load_bundled_fonts(assets_dir / "fonts")

    icon_path = assets_dir / "vn.ihoan.TahoeWidgets.svg"
    tray_svg_path = assets_dir / "vn.ihoan.TahoeWidgets-symbolic.svg"
    app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon.fromTheme("preferences-desktop-theme")
    app.setWindowIcon(app_icon)

    def current_tray_icon() -> QIcon:
        return build_symbolic_tray_icon(tray_svg_path, detect_tray_monochrome_color(app))

    store = SettingsStore()
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    stay_alive_hidden = background_mode or store.settings.keep_in_tray
    app.setQuitOnLastWindowClosed(not stay_alive_hidden)

    manager = DesktopWidgetManager(store, assets_dir)
    control_win = TahoeControlWindow(store, manager, assets_dir, tray_available or background_mode)

    manager.open_panel_requested.connect(
        lambda: (control_win.showNormal(), control_win.raise_(), control_win.activateWindow())
    )
    manager.open_settings_requested.connect(control_win.open_settings)
    manager.quit_requested.connect(control_win.force_quit)
    control_win.quit_requested.connect(app.quit)

    # Single-instance IPC server
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer(app)
    server.listen(SERVER_NAME)

    def on_ipc_connection() -> None:
        conn = server.nextPendingConnection()
        if not conn:
            return
        conn.waitForReadyRead(200)
        cmd = bytes(conn.readAll()).decode("utf-8", errors="ignore").strip()
        conn.disconnectFromServer()
        if cmd == "toggle-widgets":
            manager.toggle_all_visible()
        elif cmd == "toggle-panel":
            control_win.toggle_panel()
        elif cmd == "sync":
            manager.sync_all()
        else:
            control_win.showNormal()
            control_win.raise_()
            control_win.activateWindow()

    server.newConnection.connect(on_ipc_connection)

    tray_state: dict[str, QSystemTrayIcon | None] = {"icon": None}
    tray_actions: dict[str, QAction] = {}
    tray_attempts = {"count": 0}

    def retranslate_tray() -> None:
        tray = tray_state["icon"]
        if tray is None:
            return
        lang = resolve_language(store.settings.language)
        tray.setToolTip(tr(lang, "tray_tip"))
        if tray_actions:
            tray_actions["toggle_widgets"].setText(tr(lang, "tray_toggle_widgets"))
            tray_actions["panel"].setText(tr(lang, "menu_open_panel"))
            tray_actions["lock"].setText(tr(lang, "tray_toggle_lock"))
            tray_actions["refresh"].setText(tr(lang, "menu_refresh_weather"))
            tray_actions["settings"].setText(tr(lang, "menu_settings"))
            tray_actions["quit"].setText(tr(lang, "menu_quit"))

    def init_tray() -> bool:
        if tray_state["icon"] is not None:
            return True
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False

        tray = QSystemTrayIcon(current_tray_icon(), app)
        menu = QMenu()

        act_toggle_widgets = QAction("", menu)
        act_toggle_widgets.triggered.connect(manager.toggle_all_visible)

        act_panel = QAction("", menu)
        act_panel.triggered.connect(
            lambda: (control_win.showNormal(), control_win.raise_(), control_win.activateWindow())
        )

        act_lock = QAction("", menu)
        act_lock.triggered.connect(manager.toggle_lock)

        act_refresh = QAction("", menu)
        act_refresh.triggered.connect(manager.refresh_weather)

        act_settings = QAction("", menu)
        act_settings.triggered.connect(control_win.open_settings)

        act_quit = QAction("", menu)
        act_quit.triggered.connect(control_win.force_quit)

        menu.addAction(act_toggle_widgets)
        menu.addAction(act_panel)
        menu.addAction(act_lock)
        menu.addAction(act_refresh)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)

        tray_actions["toggle_widgets"] = act_toggle_widgets
        tray_actions["panel"] = act_panel
        tray_actions["lock"] = act_lock
        tray_actions["refresh"] = act_refresh
        tray_actions["settings"] = act_settings
        tray_actions["quit"] = act_quit

        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: manager.toggle_all_visible()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        tray_state["icon"] = tray
        retranslate_tray()
        tray.show()
        control_win._tray_available = True

        def refresh_tray_theme(*_args) -> None:
            if tray_state["icon"] is not None:
                tray_state["icon"].setIcon(current_tray_icon())
            control_win._apply_theme()
            control_win._sync_ui()

        app.paletteChanged.connect(refresh_tray_theme)
        try:
            app.styleHints().colorSchemeChanged.connect(refresh_tray_theme)
        except Exception:
            pass
        return True

    control_win.language_changed.connect(retranslate_tray)

    if not init_tray():
        tray_timer = QTimer(app)

        def retry_tray() -> None:
            tray_attempts["count"] += 1
            if init_tray() or tray_attempts["count"] >= 15:
                tray_timer.stop()

        tray_timer.timeout.connect(retry_tray)
        tray_timer.start(2000)

    # Hiển thị các widget đang bật ở đúng vị trí đã lưu
    manager.sync_all()

    if not background_mode:
        control_win.show()

    return app.exec()
