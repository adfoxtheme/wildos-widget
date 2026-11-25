"""Bảng điều khiển kéo thả widget ra màn hình & cài đặt theo phong cách Wild OS."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .i18n import resolve_language, tr
from .manager import DesktopWidgetManager
from .settings_store import SettingsStore, WidgetSettings
from .ui_components import SettingsCard, ToggleSwitch, build_theme_qss, get_wildos_palette

WIDGET_CATALOG: list[tuple[str, str]] = [
    ("clock", "#9fd38a"),
    ("weather", "#6eb5ff"),
    ("system", "#79d988"),
    ("lunar", "#ffd666"),
    ("rest", "#66d9ef"),
]


class DraggableWidgetRow(QFrame):
    """Một dòng widget trong Bảng điều khiển: hỗ trợ nút gạt mượt và kéo thẳng ra màn hình."""

    toggled = pyqtSignal(str, bool)
    dropped_outside = pyqtSignal(str, int, int)

    def __init__(
        self,
        widget_id: str,
        accent: str,
        panel_window: QMainWindow,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.widget_id = widget_id
        self._panel_window = panel_window
        self._dragging = False
        self._drag_start = QPoint()

        self.setObjectName("WidgetRow")
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(12)

        badge = QFrame()
        badge.setObjectName("DragBadge")
        badge.setFixedSize(40, 40)
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        lbl_grip = QLabel("⋮⋮")
        lbl_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_grip.setStyleSheet(f"color: {accent}; font-size: 16px; font-weight: 700; border: none;")
        badge_layout.addWidget(lbl_grip)
        layout.addWidget(badge)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("RowTitle")
        self._lbl_desc = QLabel()
        self._lbl_desc.setObjectName("RowSubtitle")
        self._lbl_pos = QLabel()
        self._lbl_pos.setStyleSheet("font-size: 10.5px; color: #9fd38a;")
        info_col.addWidget(self._lbl_title)
        info_col.addWidget(self._lbl_desc)
        info_col.addWidget(self._lbl_pos)
        layout.addLayout(info_col, 1)

        pal = get_wildos_palette()
        self._switch = ToggleSwitch(pal.accent, pal.is_dark)
        self._switch.toggled.connect(lambda checked: self.toggled.emit(self.widget_id, checked))
        layout.addWidget(self._switch)

    def sync_state(self, lang: str, enabled: bool, visible_all: bool, pos: tuple[int, int]) -> None:
        pal = get_wildos_palette()
        self.setToolTip(tr(lang, "row_drag_tip"))
        self._lbl_title.setText(tr(lang, f"cat_{self.widget_id}_title"))
        self._lbl_desc.setText(tr(lang, f"cat_{self.widget_id}_desc"))
        self._lbl_pos.setStyleSheet(f"font-size: 10.5px; color: {pal.accent};")

        self._switch.set_theme(pal.accent, pal.is_dark)
        self._switch.blockSignals(True)
        self._switch.setChecked(enabled)
        self._switch.blockSignals(False)

        if enabled and visible_all:
            self._lbl_pos.setText(tr(lang, "row_pos_shown", x=pos[0], y=pos[1]))
        elif enabled:
            self._lbl_pos.setText(tr(lang, "row_pos_hidden", x=pos[0], y=pos[1]))
        else:
            self._lbl_pos.setText(tr(lang, "row_pos_off"))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            gpos = event.globalPosition().toPoint()
            if (gpos - self._drag_start).manhattanLength() >= 20:
                if not self._panel_window.frameGeometry().contains(gpos):
                    self.dropped_outside.emit(self.widget_id, gpos.x(), gpos.y())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class SettingsDialog(QDialog):
    """Hộp thoại cài đặt thiết kế dạng danh sách thẻ mềm mại chuẩn Wild OS."""

    CONTROL_WIDTH = 220
    CONTROL_HEIGHT = 34

    def __init__(
        self,
        settings: WidgetSettings,
        parent: QWidget | None = None,
        assets_dir: Path | None = None,
    ) -> None:
        super().__init__(parent)
        lang = resolve_language(settings.language)
        pal = get_wildos_palette()
        resolved_assets = assets_dir or getattr(parent, "assets_dir", None)
        self.setWindowTitle(tr(lang, "settings_title"))
        self.setMinimumSize(540, 560)
        self.resize(560, 680)
        self.setStyleSheet(build_theme_qss(pal, resolved_assets))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("HeaderBar")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(2)
        lbl_h = QLabel(tr(lang, "settings_title"))
        lbl_h.setObjectName("AppTitle")
        lbl_sub = QLabel(tr(lang, "grp_weather"))
        lbl_sub.setObjectName("AppSubtitle")
        hl.addWidget(lbl_h)
        hl.addWidget(lbl_sub)
        root.addWidget(header)

        # Scrollable cards content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(18, 12, 18, 18)
        body.setSpacing(10)

        # Section 1: Language & Display
        sec_sys = QLabel(tr(lang, "grp_system"))
        sec_sys.setObjectName("SectionHeader")
        body.addWidget(sec_sys)

        sys_card = SettingsCard()

        def unify_input(ctrl: QWidget) -> QWidget:
            ctrl.setFixedSize(self.CONTROL_WIDTH, self.CONTROL_HEIGHT)
            return ctrl

        self.cb_lang = QComboBox()
        self.cb_lang.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cb_lang.addItem(tr(lang, "lang_auto"), "auto")
        self.cb_lang.addItem(tr(lang, "lang_vi"), "vi")
        self.cb_lang.addItem(tr(lang, "lang_en"), "en")
        self.cb_lang.setCurrentIndex(max(0, self.cb_lang.findData(settings.language)))
        sys_card.add_row(tr(lang, "lbl_lang").rstrip(":"), None, unify_input(self.cb_lang))

        self.cb_layer = QComboBox()
        self.cb_layer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cb_layer.addItem(tr(lang, "layer_bottom"), "bottom")
        self.cb_layer.addItem(tr(lang, "layer_normal"), "normal")
        self.cb_layer.addItem(tr(lang, "layer_top"), "top")
        self.cb_layer.setCurrentIndex(max(0, self.cb_layer.findData(settings.widget_layer)))
        sys_card.add_row(tr(lang, "lbl_layer").rstrip(":"), None, unify_input(self.cb_layer))

        self.chk_snap = ToggleSwitch(pal.accent, pal.is_dark)
        self.chk_snap.setChecked(settings.snap_enabled)
        sys_card.add_row(tr(lang, "chk_snap"), None, self.chk_snap)

        self.sp_gap = QSpinBox()
        self.sp_gap.setRange(0, 64)
        self.sp_gap.setSuffix(" px")
        self.sp_gap.setValue(settings.snap_gap)
        sys_card.add_row(tr(lang, "lbl_gap").rstrip(":"), None, unify_input(self.sp_gap))

        self.sp_margin = QSpinBox()
        self.sp_margin.setRange(0, 120)
        self.sp_margin.setSuffix(" px")
        self.sp_margin.setValue(settings.snap_margin)
        sys_card.add_row(tr(lang, "lbl_margin").rstrip(":"), None, unify_input(self.sp_margin))

        self.chk_lock = ToggleSwitch(pal.accent, pal.is_dark)
        self.chk_lock.setChecked(settings.lock_positions)
        sys_card.add_row(tr(lang, "chk_lock"), None, self.chk_lock)

        self.chk_tray = ToggleSwitch(pal.accent, pal.is_dark)
        self.chk_tray.setChecked(settings.keep_in_tray)
        sys_card.add_row(tr(lang, "chk_keep_tray"), None, self.chk_tray)

        self.chk_autostart = ToggleSwitch(pal.accent, pal.is_dark)
        self.chk_autostart.setChecked(settings.autostart)
        sys_card.add_row(tr(lang, "chk_autostart_full"), None, self.chk_autostart)

        body.addWidget(sys_card)

        # Section 2: Weather
        sec_w = QLabel(tr(lang, "cat_weather_title"))
        sec_w.setObjectName("SectionHeader")
        body.addWidget(sec_w)

        w_card = SettingsCard()

        self.ed_city = QLineEdit(settings.weather_city)
        self.ed_city.setPlaceholderText(tr(lang, "ph_city"))
        w_card.add_row(tr(lang, "lbl_city").rstrip(":"), None, unify_input(self.ed_city))

        self.ed_api_key = QLineEdit(settings.weather_api_key)
        self.ed_api_key.setPlaceholderText(tr(lang, "ph_api_key"))
        w_card.add_row(tr(lang, "lbl_api_key").rstrip(":"), None, unify_input(self.ed_api_key))

        self.sp_interval = QSpinBox()
        self.sp_interval.setRange(5, 120)
        self.sp_interval.setSingleStep(5)
        self.sp_interval.setSuffix(tr(lang, "suffix_minutes"))
        self.sp_interval.setValue(settings.weather_update_interval)
        w_card.add_row(tr(lang, "lbl_interval").rstrip(":"), None, unify_input(self.sp_interval))

        self.sp_lat = QDoubleSpinBox()
        self.sp_lat.setRange(-90.0, 90.0)
        self.sp_lat.setDecimals(4)
        self.sp_lat.setValue(settings.weather_lat)
        w_card.add_row(tr(lang, "lbl_lat").rstrip(":"), None, unify_input(self.sp_lat))

        self.sp_lon = QDoubleSpinBox()
        self.sp_lon.setRange(-180.0, 180.0)
        self.sp_lon.setDecimals(4)
        self.sp_lon.setValue(settings.weather_lon)
        w_card.add_row(tr(lang, "lbl_lon").rstrip(":"), None, unify_input(self.sp_lon))

        body.addWidget(w_card)
        body.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Footer
        footer = QFrame()
        footer.setObjectName("FooterBar")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(18, 11, 18, 11)
        fl.setSpacing(10)
        fl.addStretch(1)

        btn_cancel = QPushButton(tr(lang, "btn_cancel"))
        btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(tr(lang, "btn_save"))
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_save.clicked.connect(self.accept)

        fl.addWidget(btn_cancel)
        fl.addWidget(btn_save)
        root.addWidget(footer)

    def apply_to(self, settings: WidgetSettings) -> None:
        settings.weather_api_key = self.ed_api_key.text().strip()
        settings.weather_city = self.ed_city.text().strip() or "Hà Nội"
        settings.weather_lat = float(self.sp_lat.value())
        settings.weather_lon = float(self.sp_lon.value())
        settings.weather_update_interval = int(self.sp_interval.value())

        settings.language = str(self.cb_lang.currentData() or "auto")
        settings.widget_layer = str(self.cb_layer.currentData() or "bottom")
        settings.snap_gap = int(self.sp_gap.value())
        settings.snap_margin = int(self.sp_margin.value())
        settings.snap_enabled = self.chk_snap.isChecked()
        settings.lock_positions = self.chk_lock.isChecked()
        settings.keep_in_tray = self.chk_tray.isChecked()
        settings.autostart = self.chk_autostart.isChecked()


class WildOSControlWindow(QMainWindow):
    """Bảng điều khiển để kéo từng widget ra màn hình, lưu vị trí và chạy ẩn cùng OS."""

    quit_requested = pyqtSignal()
    language_changed = pyqtSignal()

    def __init__(
        self,
        store: SettingsStore,
        manager: DesktopWidgetManager,
        assets_dir: Path,
        tray_available: bool,
    ) -> None:
        super().__init__()
        self.store = store
        self.settings = store.settings
        self.manager = manager
        self.assets_dir = assets_dir
        self._tray_available = tray_available
        self._force_quit = False
        self._rows: dict[str, DraggableWidgetRow] = {}

        self.setMinimumWidth(600)
        icon_file = assets_dir / "vn.ihoan.WildOSWidget.svg"
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self._apply_theme()
        self._build_ui()
        self.manager.state_changed.connect(self._sync_ui)
        self._sync_ui()

    def _apply_theme(self) -> None:
        pal = get_wildos_palette()
        self.setStyleSheet(build_theme_qss(pal, self.assets_dir))

    def _build_ui(self) -> None:
        pal = get_wildos_palette()
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("HeaderBar")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 12, 18, 12)
        h_lay.setSpacing(8)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("AppTitle")
        self._lbl_sub = QLabel()
        self._lbl_sub.setObjectName("AppSubtitle")
        t_col.addWidget(self._lbl_title)
        t_col.addWidget(self._lbl_sub)
        h_lay.addLayout(t_col, 1)

        self._btn_visible = QPushButton()
        self._btn_visible.setCheckable(True)
        self._btn_visible.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_visible.clicked.connect(lambda: self.manager.set_all_visible(self._btn_visible.isChecked()))

        self._btn_snap = QPushButton()
        self._btn_snap.setCheckable(True)
        self._btn_snap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_snap.clicked.connect(lambda: self.manager.set_snap_enabled(self._btn_snap.isChecked()))

        self._btn_lock = QPushButton()
        self._btn_lock.setCheckable(True)
        self._btn_lock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_lock.clicked.connect(lambda: self.manager.set_locked(self._btn_lock.isChecked()))

        self._btn_settings = QPushButton()
        self._btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_settings.clicked.connect(self.open_settings)

        h_lay.addWidget(self._btn_visible)
        h_lay.addWidget(self._btn_snap)
        h_lay.addWidget(self._btn_lock)
        h_lay.addWidget(self._btn_settings)
        root.addWidget(header)

        # Widget list
        body = QWidget()
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(16, 14, 16, 14)
        b_lay.setSpacing(10)

        for wid, accent in WIDGET_CATALOG:
            row = DraggableWidgetRow(wid, accent, self)
            row.toggled.connect(self.manager.set_widget_enabled)
            row.dropped_outside.connect(self._on_row_dropped_outside)
            self._rows[wid] = row
            b_lay.addWidget(row)

        root.addWidget(body, 1)

        # Footer bar
        footer = QFrame()
        footer.setObjectName("FooterBar")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(18, 11, 18, 11)
        f_lay.setSpacing(10)

        self._chk_autostart = ToggleSwitch(pal.accent, pal.is_dark)
        self._chk_autostart.toggled.connect(self._on_autostart_toggled)
        self._lbl_autostart = QLabel()
        self._lbl_autostart.setObjectName("RowTitle")

        f_lay.addWidget(self._chk_autostart)
        f_lay.addWidget(self._lbl_autostart)
        f_lay.addStretch(1)

        self._btn_reset = QPushButton()
        self._btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_reset.clicked.connect(self.manager.reset_default_positions)

        self._btn_hide = QPushButton()
        self._btn_hide.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_hide.setObjectName("PrimaryBtn")
        self._btn_hide.clicked.connect(self.hide)

        f_lay.addWidget(self._btn_reset)
        if self._tray_available:
            f_lay.addWidget(self._btn_hide)
        root.addWidget(footer)

    def _on_row_dropped_outside(self, widget_id: str, gx: int, gy: int) -> None:
        w, h = self.manager.get_widget_size(widget_id)
        self.manager.place_widget_at(widget_id, gx - w // 2, gy - h // 2)

    def _on_autostart_toggled(self, checked: bool) -> None:
        self.settings.autostart = checked
        self.store.save()
        self.store.sync_autostart()

    def _sync_ui(self) -> None:
        pal = get_wildos_palette()
        lang = resolve_language(self.settings.language)
        self.setWindowTitle(tr(lang, "panel_title"))
        self._lbl_title.setText(tr(lang, "app_name"))
        self._lbl_sub.setText(tr(lang, "panel_subtitle"))
        self._btn_settings.setText(tr(lang, "btn_settings"))
        self._btn_reset.setText(tr(lang, "btn_reset"))
        self._btn_hide.setText(tr(lang, "btn_hide_tray"))
        self._lbl_autostart.setText(tr(lang, "chk_autostart"))
        self._btn_snap.setToolTip(tr(lang, "btn_snap_tip"))

        self._btn_visible.blockSignals(True)
        self._btn_visible.setChecked(self.settings.widgets_visible)
        self._btn_visible.setText(tr(lang, "btn_show_all_on") if self.settings.widgets_visible else tr(lang, "btn_show_all_off"))
        self._btn_visible.blockSignals(False)

        self._btn_snap.blockSignals(True)
        self._btn_snap.setChecked(self.settings.snap_enabled)
        self._btn_snap.setText(tr(lang, "btn_snap_on") if self.settings.snap_enabled else tr(lang, "btn_snap_off"))
        self._btn_snap.blockSignals(False)

        self._btn_lock.blockSignals(True)
        self._btn_lock.setChecked(self.settings.lock_positions)
        self._btn_lock.setText(tr(lang, "btn_lock_on") if self.settings.lock_positions else tr(lang, "btn_lock_off"))
        self._btn_lock.blockSignals(False)

        self._chk_autostart.set_theme(pal.accent, pal.is_dark)
        self._chk_autostart.blockSignals(True)
        self._chk_autostart.setChecked(self.settings.autostart)
        self._chk_autostart.blockSignals(False)

        for wid, row in self._rows.items():
            row.sync_state(
                lang,
                self.store.is_widget_enabled(wid),
                self.settings.widgets_visible,
                self.store.get_position(wid),
            )

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            prev_layer = self.settings.widget_layer
            prev_lang = self.settings.language
            dlg.apply_to(self.settings)
            self.store.save()
            self.store.sync_autostart()
            if prev_layer != self.settings.widget_layer:
                self.manager.apply_layer()
            self.manager.set_snap_enabled(self.settings.snap_enabled)
            self.manager.set_locked(self.settings.lock_positions)
            if prev_lang != self.settings.language:
                self.manager.refresh_language()
                self.language_changed.emit()
            else:
                self.manager.refresh_weather()
            self._sync_ui()

    def toggle_panel(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self._apply_theme()
            self._sync_ui()
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def force_quit(self) -> None:
        self._force_quit = True
        self.manager.close_all()
        self.close()
        self.quit_requested.emit()

    def closeEvent(self, event) -> None:
        if not self._force_quit and self._tray_available and self.settings.keep_in_tray:
            event.ignore()
            self.hide()
            return
        if not self._force_quit:
            self.manager.close_all()
        super().closeEvent(event)
