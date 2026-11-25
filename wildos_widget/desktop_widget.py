"""Cửa sổ thẻ nổi độc lập cho từng widget trên màn hình desktop."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import QMenu, QPushButton, QVBoxLayout, QWidget

from .i18n import tr
from .widgets import BaseCardWidget
from .x11_helpers import apply_ewmh_widget_hints


class DesktopWidgetWindow(QWidget):
    """Bọc 1 widget card thành cửa sổ nổi riêng biệt kéo thả được khắp màn hình."""

    position_changed = pyqtSignal(str, int, int)
    hide_requested = pyqtSignal(str)
    open_panel_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    toggle_lock_requested = pyqtSignal()
    toggle_snap_requested = pyqtSignal()
    reset_positions_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(
        self,
        widget_id: str,
        card: BaseCardWidget,
        snap_handler: Callable[[str, int, int, int, int], tuple[int, int]] | None = None,
        drag_end_handler: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.widget_id = widget_id
        self.card = card
        self._snap_handler = snap_handler
        self._drag_end_handler = drag_end_handler
        self._layer = "bottom"
        self._lang = "en"
        self._locked = False
        self._snap_enabled = True
        self._dragging = False
        self._moved_while_drag = False
        self._press_global_pos = QPoint()
        self._drag_offset = QPoint()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(card)

        # Nút đóng nhanh khi hover vào widget
        self._close_btn = QPushButton("×", self)
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setToolTip(tr(self._lang, "close_widget_tip"))
        self._close_btn.setStyleSheet(
            "QPushButton { background-color: rgba(20, 22, 29, 0.78); color: #ffffff; "
            "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 11px; "
            "font-size: 14px; font-weight: bold; padding-bottom: 2px; }"
            "QPushButton:hover { background-color: #d94848; border-color: #ff7b7b; }"
        )
        self._close_btn.clicked.connect(lambda: self.hide_requested.emit(self.widget_id))
        self._close_btn.hide()

        self._sync_size()
        if hasattr(card, "height_changed"):
            card.height_changed.connect(self._sync_size)

    def _sync_size(self) -> None:
        self.setFixedSize(self.card.width(), self.card.height())
        self._close_btn.move(self.width() - 32, 10)
        self._close_btn.raise_()

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        if locked:
            self._close_btn.hide()
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_snap_enabled(self, enabled: bool) -> None:
        self._snap_enabled = enabled

    def set_language(self, lang: str) -> None:
        self._lang = lang
        self._close_btn.setToolTip(tr(lang, "close_widget_tip"))
        self.card.set_language(lang)

    def apply_layer(self, layer: str) -> None:
        self._layer = layer
        was_visible = self.isVisible()
        old_pos = self.pos()
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        if layer == "top":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        elif layer == "bottom":
            flags |= Qt.WindowType.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if was_visible:
            self.show()
            self.move(old_pos)
            self._apply_x11_skip_taskbar()

    def _apply_x11_skip_taskbar(self) -> None:
        try:
            wid = int(self.winId())
        except Exception:
            return
        apply_ewmh_widget_hints(wid, self._layer)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_x11_skip_taskbar()
        QTimer.singleShot(60, self._apply_x11_skip_taskbar)

    def move_clamped(self, x: int, y: int) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geom = screen.availableGeometry()
            min_x = geom.left() - self.width() + 60
            max_x = geom.right() - 60
            min_y = geom.top()
            max_y = geom.bottom() - 60
            x = max(min_x, min(max_x, x))
            y = max(min_y, min(max_y, y))
        self.move(x, y)

    def enterEvent(self, event) -> None:
        if not self._locked:
            self._close_btn.show()
            self._close_btn.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._close_btn.hide()
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:
        if not self._locked:
            step = 10 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
            dx = dy = 0
            if event.key() == Qt.Key.Key_Left:
                dx = -step
            elif event.key() == Qt.Key.Key_Right:
                dx = step
            elif event.key() == Qt.Key.Key_Up:
                dy = -step
            elif event.key() == Qt.Key.Key_Down:
                dy = step
            if dx or dy:
                nx = self.x() + dx
                ny = self.y() + dy
                self.move_clamped(nx, ny)
                pos = self.pos()
                self.position_changed.emit(self.widget_id, pos.x(), pos.y())
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_pos = event.globalPosition().toPoint()
            self._moved_while_drag = False
            if not self._locked:
                self._dragging = True
                self._drag_offset = self._press_global_pos - self.frameGeometry().topLeft()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and not self._locked:
            gpos = event.globalPosition().toPoint()
            if (gpos - self._press_global_pos).manhattanLength() >= 6:
                self._moved_while_drag = True
            if self._moved_while_drag:
                raw = gpos - self._drag_offset
                bypass_snap = bool(
                    event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
                )
                if self._snap_handler is not None and self._snap_enabled and not bypass_snap:
                    sx, sy = self._snap_handler(self.widget_id, raw.x(), raw.y(), self.width(), self.height())
                    self.move(sx, sy)
                else:
                    if self._drag_end_handler is not None:
                        self._drag_end_handler()
                    self.move(raw)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            was_moved = self._moved_while_drag
            self._dragging = False
            self._moved_while_drag = False
            if self._drag_end_handler is not None:
                self._drag_end_handler()
            self.setCursor(Qt.CursorShape.OpenHandCursor if not self._locked else Qt.CursorShape.ArrowCursor)
            if was_moved:
                pos = self.pos()
                self.position_changed.emit(self.widget_id, pos.x(), pos.y())
            elif (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength() < 6:
                if hasattr(self.card, "on_quick_click"):
                    self.card.on_quick_click()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_context_menu(self, pos: QPoint) -> None:
        lang = self._lang
        menu = QMenu(self)
        act_lock = QAction(tr(lang, "menu_unlock") if self._locked else tr(lang, "menu_lock"), self)
        act_lock.triggered.connect(self.toggle_lock_requested.emit)

        act_snap = QAction(tr(lang, "menu_snap"), self)
        act_snap.setCheckable(True)
        act_snap.setChecked(self._snap_enabled)
        act_snap.triggered.connect(self.toggle_snap_requested.emit)

        act_reset = QAction(tr(lang, "menu_reset"), self)
        act_reset.triggered.connect(self.reset_positions_requested.emit)

        act_hide = QAction(tr(lang, "menu_hide_widget"), self)
        act_hide.triggered.connect(lambda: self.hide_requested.emit(self.widget_id))

        act_panel = QAction(tr(lang, "menu_open_panel"), self)
        act_panel.triggered.connect(self.open_panel_requested.emit)

        act_refresh = QAction(tr(lang, "menu_refresh_weather"), self)
        act_refresh.triggered.connect(self.refresh_requested.emit)

        act_settings = QAction(tr(lang, "menu_settings"), self)
        act_settings.triggered.connect(self.open_settings_requested.emit)

        act_quit = QAction(tr(lang, "menu_quit"), self)
        act_quit.triggered.connect(self.quit_requested.emit)

        menu.addAction(act_lock)
        menu.addAction(act_snap)
        menu.addAction(act_reset)
        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_panel)
        menu.addAction(act_refresh)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        menu.exec(self.mapToGlobal(pos))
