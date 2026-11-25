"""Thành phần giao diện mềm mại theo phong cách Wild OS (ToggleSwitch, SettingsCard, Theme thích ứng Dark/Light)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter, QPalette
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ThemePalette:
    is_dark: bool
    bg: str
    header_bg: str
    card_bg: str
    card_hover: str
    input_bg: str
    btn_bg: str
    btn_hover: str
    border: str
    divider: str
    text: str
    subtext: str
    accent: str
    accent_hover: str
    accent_text: str


def get_wildos_palette(app: QApplication | None = None) -> ThemePalette:
    """Lấy bảng màu đồng bộ với Wild OS (Dark: #181a22 + #9fd38a; Light: sáng dịu + #5c8d4c)."""
    is_dark = True
    accent_hex = "#9fd38a"

    inst = app or QApplication.instance()
    if inst is not None:
        try:
            scheme = inst.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                is_dark = False
            elif scheme == Qt.ColorScheme.Dark:
                is_dark = True
            else:
                bg_col = inst.palette().color(QPalette.ColorRole.Window)
                is_dark = bg_col.lightnessF() < 0.5
        except Exception:
            pass

        hl = inst.palette().color(QPalette.ColorRole.Highlight)
        if hl.isValid() and hl.saturation() > 30:
            accent_hex = hl.name()

    if is_dark:
        accent_col = QColor(accent_hex)
        # Nếu accent quá tối trong theme dark, ưu tiên xanh sage đặc trưng của Wild OS
        if accent_col.lightnessF() < 0.48:
            accent_hex = "#9fd38a"
        accent_hover = QColor(accent_hex).lighter(110).name()
        return ThemePalette(
            is_dark=True,
            bg="#181a22",
            header_bg="#14161d",
            card_bg="#20232d",
            card_hover="#252935",
            input_bg="#14161d",
            btn_bg="#262934",
            btn_hover="#2f3340",
            border="rgba(255, 255, 255, 0.08)",
            divider="rgba(255, 255, 255, 0.06)",
            text="#f4f6fa",
            subtext="rgba(255, 255, 255, 0.58)",
            accent=accent_hex,
            accent_hover=accent_hover,
            accent_text="#111418",
        )

    accent_col = QColor(accent_hex)
    if accent_col.lightnessF() > 0.65:
        accent_hex = "#5a8f49"
    accent_hover = QColor(accent_hex).darker(110).name()
    return ThemePalette(
        is_dark=False,
        bg="#f3f4f7",
        header_bg="#eaecf0",
        card_bg="#ffffff",
        card_hover="#f8f9fb",
        input_bg="#f3f4f7",
        btn_bg="#e6e8ee",
        btn_hover="#dce0e8",
        border="rgba(0, 0, 0, 0.08)",
        divider="rgba(0, 0, 0, 0.06)",
        text="#1d2026",
        subtext="rgba(29, 32, 38, 0.62)",
        accent=accent_hex,
        accent_hover=accent_hover,
        accent_text="#ffffff",
    )


def build_theme_qss(pal: ThemePalette, assets_dir: Path | None = None) -> str:
    tone = "dark" if pal.is_dark else "light"
    default_ui_dir = Path(__file__).resolve().parent.parent / "assets" / "ui"
    if assets_dir is not None and (assets_dir / "ui").exists():
        ui_dir = assets_dir / "ui"
    else:
        ui_dir = default_ui_dir
    up_svg = (ui_dir / f"chevron-up-{tone}.svg").as_posix()
    down_svg = (ui_dir / f"chevron-down-{tone}.svg").as_posix()

    return f"""
QMainWindow, QDialog {{
    background-color: {pal.bg};
    color: {pal.text};
    font-family: "SF Pro Text", "Noto Sans", sans-serif;
}}
QWidget, QPushButton, QCheckBox, QComboBox, QAbstractButton {{
    outline: none;
}}
QFrame#HeaderBar {{
    background-color: {pal.header_bg};
    border-bottom: 1px solid {pal.border};
}}
QFrame#FooterBar {{
    background-color: {pal.header_bg};
    border-top: 1px solid {pal.border};
}}
QLabel#AppTitle {{
    font-family: "SF Pro Display", "Noto Sans", sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: {pal.text};
}}
QLabel#AppSubtitle {{
    font-size: 11.5px;
    color: {pal.subtext};
}}
QLabel#SectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: {pal.accent};
    padding: 4px 4px 2px 4px;
}}
QFrame#SettingsCard, QFrame#WidgetRow {{
    background-color: {pal.card_bg};
    border: 1px solid {pal.border};
    border-radius: 14px;
}}
QFrame#WidgetRow:hover {{
    background-color: {pal.card_hover};
    border-color: {pal.accent};
}}
QFrame#RowDivider {{
    background-color: {pal.divider};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame#DragBadge {{
    background-color: {pal.btn_bg};
    border: 1px dashed {pal.border};
    border-radius: 10px;
}}
QLabel#RowTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {pal.text};
}}
QLabel#RowSubtitle {{
    font-size: 11px;
    color: {pal.subtext};
}}
QPushButton {{
    background-color: {pal.btn_bg};
    color: {pal.text};
    border: 1px solid {pal.border};
    border-radius: 10px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {pal.btn_hover};
}}
QPushButton:checked {{
    background-color: {pal.accent};
    border-color: {pal.accent};
    color: {pal.accent_text};
}}
QPushButton#PrimaryBtn {{
    background-color: {pal.accent};
    border-color: {pal.accent};
    color: {pal.accent_text};
}}
QPushButton#PrimaryBtn:hover {{
    background-color: {pal.accent_hover};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {pal.input_bg};
    color: {pal.text};
    border: 1px solid {pal.border};
    border-radius: 9px;
    padding: 0px 10px;
    font-size: 12px;
}}
QComboBox, QSpinBox, QDoubleSpinBox {{
    padding-right: 30px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {pal.accent};
}}
QComboBox::drop-down {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    border-left: 1px solid {pal.divider};
    border-top-right-radius: 9px;
    border-bottom-right-radius: 9px;
    background: transparent;
}}
QComboBox::drop-down:hover {{
    background-color: {pal.btn_hover};
}}
QComboBox::down-arrow {{
    image: url("{down_svg}");
    width: 11px;
    height: 11px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    height: 16px;
    border: none;
    border-left: 1px solid {pal.divider};
    border-top-right-radius: 9px;
    background: transparent;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 28px;
    height: 16px;
    border: none;
    border-left: 1px solid {pal.divider};
    border-top: 1px solid {pal.divider};
    border-bottom-right-radius: 9px;
    background: transparent;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {pal.btn_hover};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{up_svg}");
    width: 10px;
    height: 10px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{down_svg}");
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {pal.card_bg};
    color: {pal.text};
    border: 1px solid {pal.border};
    border-radius: 8px;
    selection-background-color: {pal.accent};
    selection-color: {pal.accent_text};
    outline: none;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 1px 4px 1px;
}}
QScrollBar::handle:vertical {{
    background: {pal.border};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


class ToggleSwitch(QAbstractButton):
    """Nút gạt viên thuốc mượt mà (phong cách Kirigami / macOS / Wild OS)."""

    def __init__(self, accent_hex: str = "#9fd38a", is_dark: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)

        self._accent = QColor(accent_hex)
        self._is_dark = is_dark
        self._pos = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)
        self.toggled.connect(self._start_anim)

    def set_theme(self, accent_hex: str, is_dark: bool) -> None:
        self._accent = QColor(accent_hex)
        self._is_dark = is_dark
        self.update()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._anim.stop()
        self._pos = 1.0 if checked else 0.0
        self.update()

    def _on_anim_value(self, val) -> None:
        self._pos = float(val)
        self.update()

    def _start_anim(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        r = h / 2.0
        off_track = QColor(255, 255, 255, 42) if self._is_dark else QColor(0, 0, 0, 42)
        if self.underMouse() and not self.isChecked():
            off_track = QColor(255, 255, 255, 62) if self._is_dark else QColor(0, 0, 0, 62)

        # Pha màu track từ off -> accent
        t = self._pos
        track_color = QColor(
            round(off_track.red() * (1 - t) + self._accent.red() * t),
            round(off_track.green() * (1 - t) + self._accent.green() * t),
            round(off_track.blue() * (1 - t) + self._accent.blue() * t),
            round(off_track.alpha() * (1 - t) + 255 * t),
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        thumb_d = 18.0
        pad = 3.0
        thumb_x = pad + t * (w - thumb_d - 2 * pad)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(thumb_x, pad, thumb_d, thumb_d))


class SettingsCard(QFrame):
    """Thẻ bo tròn chứa danh sách các dòng cài đặt có đường ngăn mảnh."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 2, 0, 2)
        self._layout.setSpacing(0)
        self._row_count = 0

    def add_row(self, title: str, subtitle: str | None, control: QWidget) -> None:
        if self._row_count > 0:
            div = QFrame()
            div.setObjectName("RowDivider")
            div_wrap = QWidget()
            dl = QHBoxLayout(div_wrap)
            dl.setContentsMargins(14, 0, 14, 0)
            dl.addWidget(div)
            self._layout.addWidget(div_wrap)

        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(14)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setObjectName("RowTitle")
        text_col.addWidget(lbl_t)
        if subtitle:
            lbl_s = QLabel(subtitle)
            lbl_s.setObjectName("RowSubtitle")
            lbl_s.setWordWrap(True)
            text_col.addWidget(lbl_s)

        lay.addLayout(text_col, 1)
        lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        self._layout.addWidget(row)
        self._row_count += 1
