"""Các hàm vẽ QPainter mô phỏng chính xác phong cách MacTahoe Cairo."""

from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication


def rgba(r: float, g: float, b: float, a: float = 1.0) -> QColor:
    return QColor.fromRgbF(
        max(0.0, min(1.0, r)),
        max(0.0, min(1.0, g)),
        max(0.0, min(1.0, b)),
        max(0.0, min(1.0, a)),
    )


COLORS = {
    "white": rgba(1.00, 1.00, 1.00, 1.00),
    "weatherSub": rgba(0.84, 0.91, 1.00, 0.90),
    "weatherMuted": rgba(0.76, 0.86, 0.99, 0.76),
    "sysText": rgba(0.96, 0.97, 1.00, 1.00),
    "sysSub": rgba(0.68, 0.72, 0.80, 0.92),
    "sysMuted": rgba(0.58, 0.62, 0.70, 0.84),
    "blue": rgba(0.30, 0.64, 1.00, 1.00),
    "green": rgba(0.19, 0.82, 0.35, 1.00),
    "purple": rgba(0.75, 0.35, 0.95, 1.00),
    "orange": rgba(1.00, 0.62, 0.04, 1.00),
    "cyan": rgba(0.25, 0.78, 0.92, 1.00),
    "gold": rgba(1.00, 0.84, 0.30, 1.00),
}


def load_bundled_fonts(fonts_dir: Path) -> None:
    """Nạp font SF Pro đi kèm ứng dụng nếu có."""
    if not fonts_dir.exists():
        return
    for font_file in sorted(fonts_dir.glob("*.otf")):
        QFontDatabase.addApplicationFont(str(font_file))


def make_font(family: str, pixel_size: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(1, round(pixel_size)))
    font.setWeight(weight)
    return font


def draw_card(
    p: QPainter,
    w: float,
    h: float,
    radius: float,
    top: tuple[float, float, float, float],
    bottom: tuple[float, float, float, float],
    border: float = 0.16,
    hovered: bool = False,
) -> None:
    rect = QRectF(0, 0, w, h)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0.0, rgba(top[0], top[1], top[2], top[3] * 0.96))
    grad.setColorAt(1.0, rgba(bottom[0], bottom[1], bottom[2], bottom[3] * 0.96))
    p.fillPath(path, grad)

    p.save()
    p.setClipPath(path)
    sheen = QLinearGradient(0, 0, 0, h * 0.62)
    sheen.setColorAt(0.0, rgba(1, 1, 1, 0.17 if hovered else 0.13))
    sheen.setColorAt(1.0, rgba(1, 1, 1, 0.0))
    p.fillRect(rect, sheen)
    p.restore()

    if border:
        edge_alpha = min(0.32 if hovered else 0.24, border + (0.12 if hovered else 0.06))
        pen = QPen(
            rgba(
                top[0] * 0.45 + 0.55,
                top[1] * 0.45 + 0.55,
                top[2] * 0.45 + 0.55,
                edge_alpha,
            ),
            1.0,
        )
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border_path = QPainterPath()
        border_path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius - 0.5, radius - 0.5)
        p.drawPath(border_path)


def draw_text(
    p: QPainter,
    x: float,
    y: float,
    text: str,
    size: float,
    color: QColor,
    bold: bool = False,
    align: str = "left",
    family: str = "SF Pro Text",
) -> None:
    if not text:
        return
    p.save()
    font = make_font(family, size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
    p.setFont(font)
    p.setPen(color)
    fm = QFontMetricsF(font)
    text_w = fm.horizontalAdvance(text)
    draw_x = x
    if align == "right":
        draw_x = x - text_w
    elif align == "center":
        draw_x = x - text_w / 2.0
    p.drawText(QPointF(draw_x, y), text)
    p.restore()


def draw_glass_text(
    p: QPainter,
    x: float,
    y: float,
    text: str,
    size: float,
    family: str = "SF Pro Rounded",
    weight: QFont.Weight = QFont.Weight.DemiBold,
) -> float:
    """Vẽ chữ hiệu ứng kính mờ gradient + viền sáng, trả về chiều rộng chữ."""
    if not text:
        return 0.0
    p.save()
    font = make_font(family, size, weight)
    fm = QFontMetricsF(font)
    path = QPainterPath()
    path.addText(QPointF(x, y), font, text)
    bounds = path.boundingRect()

    grad = QLinearGradient(x, bounds.top(), x, bounds.bottom())
    grad.setColorAt(0.0, rgba(1.0, 1.0, 1.0, 0.52))
    grad.setColorAt(0.5, rgba(1.0, 1.0, 1.0, 0.20))
    grad.setColorAt(1.0, rgba(1.0, 1.0, 1.0, 0.04))

    p.setPen(QPen(rgba(1.0, 1.0, 1.0, 0.68), 1.15))
    p.setBrush(grad)
    p.drawPath(path)
    p.restore()
    return fm.horizontalAdvance(text)


def draw_progress_bar(
    p: QPainter, x: float, y: float, w: float, h: float, percent: float, color: QColor
) -> None:
    pct = max(0.0, min(100.0, float(percent)))
    bg_path = QPainterPath()
    bg_path.addRoundedRect(QRectF(x, y, w, h), h / 2.0, h / 2.0)
    p.fillPath(bg_path, rgba(1.0, 1.0, 1.0, 0.11))
    if pct <= 0:
        return
    fill_w = max(h, (w * pct) / 100.0)
    fg_path = QPainterPath()
    fg_path.addRoundedRect(QRectF(x, y, fill_w, h), h / 2.0, h / 2.0)
    p.fillPath(fg_path, color)


def draw_system_icon(p: QPainter, kind: str, x: float, y: float, color: QColor) -> None:
    p.save()
    p.translate(x, y)
    p.scale(0.82, 0.82)
    p.translate(-x, -y)

    bg_color = QColor(color)
    bg_color.setAlphaF(0.14)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg_color)
    p.drawEllipse(QPointF(x + 9, y + 8), 8.5, 8.5)

    stroke_color = QColor(color)
    stroke_color.setAlphaF(0.95)
    p.setPen(QPen(stroke_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(x + 3, y + 2, 12, 12), 2, 2)

    if kind == "cpu":
        p.drawRoundedRect(QRectF(x + 7, y + 6, 4, 4), 1, 1)
        for offset in range(3):
            pin = x + 6 + offset * 3
            p.drawLine(QPointF(pin, y + 1), QPointF(pin, y + 3))
            p.drawLine(QPointF(pin, y + 13), QPointF(pin, y + 15))
    elif kind == "gpu":
        p.drawEllipse(QPointF(x + 6, y + 8.5), 2.2, 2.2)
        p.drawLine(QPointF(x + 10, y + 7), QPointF(x + 13, y + 7))
        p.drawLine(QPointF(x + 10, y + 10), QPointF(x + 13, y + 10))
        p.drawLine(QPointF(x + 5, y + 14), QPointF(x + 5, y + 15))
    elif kind == "ram":
        p.drawLine(QPointF(x + 5, y + 6), QPointF(x + 13, y + 6))
        p.drawLine(QPointF(x + 5, y + 10), QPointF(x + 13, y + 10))
        for pin in range(4):
            pin_x = x + 6 + pin * 2
            p.drawLine(QPointF(pin_x, y + 6), QPointF(pin_x, y + 5))
            p.drawLine(QPointF(pin_x, y + 10), QPointF(pin_x, y + 11))
    elif kind == "ssd":
        p.setBrush(stroke_color)
        p.drawEllipse(QPointF(x + 5, y + 8), 1.3, 1.3)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(x + 9, y + 6), QPointF(x + 13, y + 6))
        p.drawLine(QPointF(x + 9, y + 8), QPointF(x + 13, y + 8))
        p.drawLine(QPointF(x + 9, y + 10), QPointF(x + 13, y + 10))
    elif kind == "network":
        p.drawLine(QPointF(x + 6, y + 6), QPointF(x + 12, y + 6))
        p.drawLine(QPointF(x + 12, y + 6), QPointF(x + 9, y + 12))
        p.drawLine(QPointF(x + 9, y + 12), QPointF(x + 6, y + 6))
        p.setBrush(stroke_color)
        p.drawEllipse(QPointF(x + 6, y + 6), 1.6, 1.6)
        p.drawEllipse(QPointF(x + 12, y + 6), 1.6, 1.6)
        p.drawEllipse(QPointF(x + 9, y + 12), 1.6, 1.6)
    p.restore()


def draw_moon_watermark(p: QPainter, x: float, y: float, r: float) -> None:
    p.save()
    path = QPainterPath()
    path.moveTo(x + r * 0.32, y - r * 0.92)
    path.cubicTo(
        x - r * 0.32, y - r * 1.02,
        x - r * 0.92, y - r * 0.48,
        x - r * 0.86, y + r * 0.08,
    )
    path.cubicTo(
        x - r * 0.72, y + r * 0.88,
        x + r * 0.20, y + r * 1.04,
        x + r * 0.76, y + r * 0.50,
    )
    path.cubicTo(
        x + r * 0.18, y + r * 0.72,
        x - r * 0.08, y + r * 0.10,
        x + r * 0.12, y - r * 0.38,
    )
    path.cubicTo(
        x + r * 0.20, y - r * 0.62,
        x + r * 0.38, y - r * 0.78,
        x + r * 0.32, y - r * 0.92,
    )
    path.closeSubpath()
    p.fillPath(path, rgba(1.0, 0.84, 0.30, 0.12))

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(rgba(1.0, 1.0, 1.0, 0.16))
    p.drawEllipse(QPointF(x - 33, y + 31), 2.2, 2.2)
    p.drawEllipse(QPointF(x - 76, y), 1.6, 1.6)
    p.restore()


def draw_rest_clock_watermark(p: QPainter, x: float, y: float, r: float) -> None:
    p.save()
    pen = QPen(rgba(1.0, 1.0, 1.0, 0.08), 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(x, y), r, r)
    p.setPen(QPen(rgba(1.0, 1.0, 1.0, 0.08), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(x, y), QPointF(x, y - 16))
    p.drawLine(QPointF(x, y), QPointF(x + 12, y + 8))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(rgba(1.0, 1.0, 1.0, 0.08))
    p.drawEllipse(QPointF(x, y), 3.0, 3.0)
    p.restore()


def draw_svg_icon(p: QPainter, icon_path: str | None, x: int, y: int, size: int) -> None:
    if not icon_path:
        return
    pixmap = QIcon(icon_path).pixmap(size, size)
    if not pixmap.isNull():
        p.drawPixmap(x, y, size, size, pixmap)


def detect_tray_monochrome_color(app: QApplication) -> str:
    """Trả về màu icon khay hệ thống theo theme tối/sáng của Wild OS / KDE."""
    try:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "#eff0f1"
        if scheme == Qt.ColorScheme.Light:
            return "#232629"
    except Exception:
        pass

    pal = app.palette()
    bg = pal.color(QPalette.ColorRole.Window)
    if bg.lightnessF() < 0.5:
        return "#eff0f1"
    return "#232629"


def build_symbolic_tray_icon(svg_path: Path, color_hex: str) -> QIcon:
    """Render SVG đơn sắc theo màu theme hiện tại ở các kích thước chuẩn khay hệ thống."""
    if not svg_path.exists():
        return QIcon.fromTheme("preferences-desktop-theme-symbolic")

    raw_svg = svg_path.read_text(encoding="utf-8")
    tinted_svg = raw_svg.replace("currentColor", color_hex).replace("#232629", color_hex)

    icon = QIcon()
    for sz in (16, 22, 24, 32, 48):
        sized_svg = tinted_svg.replace('width="22" height="22"', f'width="{sz}" height="{sz}"')
        data = QByteArray(sized_svg.encode("utf-8"))
        pm = QPixmap()
        if pm.loadFromData(data, "SVG"):
            icon.addPixmap(pm)
    return icon
