"""Quản lý vòng đời, vị trí và đường gióng căn chỉnh của từng widget nổi trên màn hình."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from .desktop_widget import DesktopWidgetWindow
from .i18n import resolve_language
from .settings_store import SettingsStore, WIDGET_IDS
from .snap_engine import Rect, compute_snap
from .snap_overlay import SnapGuideOverlay
from .widgets import (
    BaseCardWidget,
    ClockWidget,
    LunarWidget,
    RestWidget,
    SystemWidget,
    WeatherWidget,
)


class DesktopWidgetManager(QObject):
    """Đồng bộ trạng thái, tọa độ, đường gióng và lớp hiển thị của các widget trên desktop."""

    state_changed = pyqtSignal()
    open_panel_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, store: SettingsStore, assets_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.settings = store.settings
        self.icons_dir = assets_dir / "weather-icons"
        self._windows: dict[str, DesktopWidgetWindow] = {}
        self._overlay = SnapGuideOverlay()

    def active_language(self) -> str:
        return resolve_language(self.settings.language)

    def _create_card(self, widget_id: str) -> BaseCardWidget:
        lang = self.active_language()
        if widget_id == "clock":
            return ClockWidget(lang)
        if widget_id == "weather":
            return WeatherWidget(self.settings, self.icons_dir, lang)
        if widget_id == "system":
            return SystemWidget(lang)
        if widget_id == "lunar":
            return LunarWidget(lang)
        if widget_id == "rest":
            return RestWidget(lang)
        raise ValueError(f"Unknown widget id: {widget_id}")

    def _screen_rect_for(self, x: int, y: int, w: int, h: int) -> Rect:
        screen = QGuiApplication.screenAt(QPoint(x + w // 2, y + h // 2)) or QGuiApplication.primaryScreen()
        if screen is None:
            return Rect(0, 0, 1920, 1080)
        g = screen.availableGeometry()
        return Rect(g.x(), g.y(), g.width(), g.height())

    def _snap_widget_move(self, widget_id: str, raw_x: int, raw_y: int, w: int, h: int) -> tuple[int, int]:
        if not self.settings.snap_enabled:
            self._overlay.clear_and_hide()
            return raw_x, raw_y

        others = [
            Rect(win.x(), win.y(), win.width(), win.height())
            for wid, win in self._windows.items()
            if wid != widget_id and win.isVisible()
        ]
        srect = self._screen_rect_for(raw_x, raw_y, w, h)
        result = compute_snap(
            Rect(raw_x, raw_y, w, h),
            others,
            srect,
            threshold=10,
            edge_margin=max(0, int(self.settings.snap_margin)),
            card_gap=max(0, int(self.settings.snap_gap)),
        )
        self._overlay.show_guides((srect.x, srect.y, srect.w, srect.h), result.guides, result.badges)
        return result.x, result.y

    def _end_widget_drag(self) -> None:
        self._overlay.clear_and_hide()

    def _ensure_window(self, widget_id: str) -> DesktopWidgetWindow:
        win = self._windows.get(widget_id)
        if win is not None:
            return win

        card = self._create_card(widget_id)
        win = DesktopWidgetWindow(
            widget_id,
            card,
            snap_handler=self._snap_widget_move,
            drag_end_handler=self._end_widget_drag,
        )
        win.apply_layer(self.settings.widget_layer)
        win.set_locked(self.settings.lock_positions)
        win.set_snap_enabled(self.settings.snap_enabled)
        win.set_language(self.active_language())

        win.position_changed.connect(self._on_widget_moved)
        win.hide_requested.connect(self.hide_single_widget)
        win.open_panel_requested.connect(self.open_panel_requested.emit)
        win.open_settings_requested.connect(self.open_settings_requested.emit)
        win.toggle_lock_requested.connect(self.toggle_lock)
        win.toggle_snap_requested.connect(self.toggle_snap)
        win.reset_positions_requested.connect(self.reset_default_positions)
        win.refresh_requested.connect(self.refresh_weather)
        win.quit_requested.connect(self.quit_requested.emit)

        self._windows[widget_id] = win
        return win

    def sync_all(self) -> None:
        """Hiển thị hoặc ẩn từng widget theo cấu hình đã lưu."""
        for wid in WIDGET_IDS:
            enabled = self.store.is_widget_enabled(wid)
            should_show = enabled and self.settings.widgets_visible
            if should_show:
                win = self._ensure_window(wid)
                x, y = self.store.get_position(wid)
                win.set_locked(self.settings.lock_positions)
                win.set_snap_enabled(self.settings.snap_enabled)
                win.show()
                win.move_clamped(x, y)
            else:
                win = self._windows.get(wid)
                if win is not None:
                    win.hide()
        self.state_changed.emit()

    def _on_widget_moved(self, widget_id: str, x: int, y: int) -> None:
        self.store.set_position(widget_id, x, y)
        self.store.save()
        self.state_changed.emit()

    def set_widget_enabled(self, widget_id: str, enabled: bool) -> None:
        self.store.set_widget_enabled(widget_id, enabled)
        if enabled:
            self.settings.widgets_visible = True
        self.store.save()
        self.sync_all()

    def place_widget_at(self, widget_id: str, x: int, y: int) -> None:
        """Bật widget và đặt tại tọa độ vừa kéo thả (có hít căn chỉnh nếu bật)."""
        self.store.set_widget_enabled(widget_id, True)
        self.settings.widgets_visible = True
        win = self._ensure_window(widget_id)
        if self.settings.snap_enabled:
            x, y = self._snap_widget_move(widget_id, x, y, win.width(), win.height())
            self._end_widget_drag()
        win.show()
        win.move_clamped(x, y)
        pos = win.pos()
        self.store.set_position(widget_id, pos.x(), pos.y())
        self.store.save()
        self.state_changed.emit()

    def hide_single_widget(self, widget_id: str) -> None:
        self.store.set_widget_enabled(widget_id, False)
        self.store.save()
        self.sync_all()

    def set_all_visible(self, visible: bool) -> None:
        self.settings.widgets_visible = visible
        self.store.save()
        self.sync_all()

    def toggle_all_visible(self) -> None:
        self.set_all_visible(not self.settings.widgets_visible)

    def set_locked(self, locked: bool) -> None:
        self.settings.lock_positions = locked
        self.store.save()
        for win in self._windows.values():
            win.set_locked(locked)
        self.state_changed.emit()

    def toggle_lock(self) -> None:
        self.set_locked(not self.settings.lock_positions)

    def set_snap_enabled(self, enabled: bool) -> None:
        self.settings.snap_enabled = enabled
        self.store.save()
        for win in self._windows.values():
            win.set_snap_enabled(enabled)
        if not enabled:
            self._overlay.clear_and_hide()
        self.state_changed.emit()

    def toggle_snap(self) -> None:
        self.set_snap_enabled(not self.settings.snap_enabled)

    def apply_layer(self) -> None:
        for win in self._windows.values():
            win.apply_layer(self.settings.widget_layer)

    def refresh_weather(self) -> None:
        win = self._windows.get("weather")
        if win is not None and isinstance(win.card, WeatherWidget):
            win.card.update_settings(self.settings)

    def refresh_language(self) -> None:
        lang = self.active_language()
        for win in self._windows.values():
            win.set_language(lang)
        self.state_changed.emit()

    def reset_default_positions(self) -> None:
        """Xếp lại 5 widget theo lề và khoảng cách chuẩn đang cấu hình."""
        margin = max(0, int(self.settings.snap_margin))
        gap = max(0, int(self.settings.snap_gap))
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geom = screen.availableGeometry()
            left_x = geom.left() + margin
            top_y = geom.top() + margin
            right_x = max(left_x + 340 + gap, geom.right() + 1 - 340 - margin)
        else:
            left_x, top_y, right_x = margin, margin, 1160

        clock_h = 210
        weather_h = 210
        lunar_h = 150

        layout_map = {
            "clock": (left_x, top_y),
            "lunar": (left_x, top_y + clock_h + gap),
            "rest": (left_x, top_y + clock_h + gap + lunar_h + gap),
            "weather": (right_x, top_y),
            "system": (right_x, top_y + weather_h + gap),
        }
        for wid, (x, y) in layout_map.items():
            self.store.set_position(wid, x, y)
        self.store.save()
        self.sync_all()

    def get_widget_size(self, widget_id: str) -> tuple[int, int]:
        win = self._windows.get(widget_id)
        if win is not None:
            return win.width(), win.height()
        sizes = {
            "clock": (340, 210),
            "weather": (340, 210),
            "system": (340, 258),
            "lunar": (340, 150),
            "rest": (340, 165),
        }
        return sizes.get(widget_id, (340, 180))

    def close_all(self) -> None:
        self._overlay.close()
        for win in self._windows.values():
            win.close()
        self._windows.clear()
