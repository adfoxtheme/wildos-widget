"""Lớp phủ trong suốt hiển thị đường gióng thông minh và nhãn khoảng cách px khi kéo widget."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from .snap_engine import GapBadge, GuideLine
from .x11_helpers import apply_ewmh_widget_hints


class SnapGuideOverlay(QWidget):
    """Overlay xuyên chuột chỉ hiện trong lúc kéo widget để căn thẳng hàng & khoảng cách."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._guides: tuple[GuideLine, ...] = ()
        self._badges: tuple[GapBadge, ...] = ()

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def show_guides(
        self,
        screen_geom: QRectF | tuple[int, int, int, int],
        guides: tuple[GuideLine, ...],
        badges: tuple[GapBadge, ...],
    ) -> None:
        if isinstance(screen_geom, tuple):
            sx, sy, sw, sh = screen_geom
        else:
            sx = int(screen_geom.x())
            sy = int(screen_geom.y())
            sw = int(screen_geom.width())
            sh = int(screen_geom.height())

        self._guides = guides
        self._badges = badges
        if not guides and not badges:
            self.hide()
            return

        self.setGeometry(sx, sy, sw, sh)
        if not self.isVisible():
            self.show()
            try:
                apply_ewmh_widget_hints(int(self.winId()), "top")
            except Exception:
                pass
        self.update()

    def clear_and_hide(self) -> None:
        self._guides = ()
        self._badges = ()
        if self.isVisible():
            self.hide()

    def paintEvent(self, event) -> None:
        if not self._guides and not self._badges:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        ox = self.x()
        oy = self.y()

        # Vẽ đường gióng với viền tối mảnh để rõ trên mọi hình nền
        halo_pen = QPen(QColor(0, 0, 0, 110), 2.5, Qt.PenStyle.DashLine)
        guide_pen = QPen(QColor(96, 165, 250, 225), 1.2, Qt.PenStyle.DashLine)

        for g in self._guides:
            if g.orientation == "v":
                x = g.pos - ox
                p1 = QPointF(x, g.start - oy)
                p2 = QPointF(x, g.end - oy)
            else:
                y = g.pos - oy
                p1 = QPointF(g.start - ox, y)
                p2 = QPointF(g.end - ox, y)
            p.setPen(halo_pen)
            p.drawLine(p1, p2)
            p.setPen(guide_pen)
            p.drawLine(p1, p2)

        # Vẽ đoạn đo khoảng cách + nhãn "14 px" / "24 px"
        measure_pen = QPen(QColor(96, 165, 250, 235), 1.4)
        font = QFont("SF Pro Text", 10)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Bold)
        p.setFont(font)
        fm = QFontMetricsF(font)

        for b in self._badges:
            p1 = QPointF(b.x1 - ox, b.y1 - oy)
            p2 = QPointF(b.x2 - ox, b.y2 - oy)
            p.setPen(measure_pen)
            p.drawLine(p1, p2)

            # Gạch đầu mút nhỏ
            if b.orientation == "v":
                p.drawLine(QPointF(p1.x() - 4, p1.y()), QPointF(p1.x() + 4, p1.y()))
                p.drawLine(QPointF(p2.x() - 4, p2.y()), QPointF(p2.x() + 4, p2.y()))
            else:
                p.drawLine(QPointF(p1.x(), p1.y() - 4), QPointF(p1.x(), p1.y() + 4))
                p.drawLine(QPointF(p2.x(), p2.y() - 4), QPointF(p2.x(), p2.y() + 4))

            tw = fm.horizontalAdvance(b.label)
            th = fm.height()
            pw = tw + 12
            ph = th + 4
            cx = (p1.x() + p2.x()) / 2.0
            cy = (p1.y() + p2.y()) / 2.0
            pill = QRectF(cx - pw / 2.0, cy - ph / 2.0, pw, ph)

            p.setPen(QPen(QColor(96, 165, 250, 200), 1.0))
            p.setBrush(QColor(16, 18, 26, 230))
            p.drawRoundedRect(pill, 6, 6)

            p.setPen(QColor(255, 255, 255, 245))
            p.drawText(pill, Qt.AlignmentFlag.AlignCenter, b.label)
