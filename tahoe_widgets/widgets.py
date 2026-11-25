"""5 widget card PyQt6 (hỗ trợ Tiếng Anh / Tiếng Việt; riêng Âm lịch luôn Tiếng Việt)."""

from __future__ import annotations

import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetricsF, QPainter
from PyQt6.QtWidgets import QWidget

from . import drawing
from .i18n import EN_MONTHS_SHORT, EN_WEEKDAYS_LONG, tr
from .lunar_calc import WEEKDAYS, get_today_lunar
from .settings_store import WidgetSettings
from .system_metrics import SystemMetrics, SystemMetricsReader, read_uptime_seconds
from .weather_service import WeatherData, fetch_weather

CARD_RADIUS = 10


def _launch_first_available(commands: list[list[str]]) -> None:
    for cmd in commands:
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue


class BaseCardWidget(QWidget):
    """Widget card nền có hỗ trợ hover và phân biệt click nhanh với kéo thả."""

    def __init__(self, width: int, height: int, lang: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._card_width = width
        self._card_height = height
        self._lang = lang
        self._hovered = False
        self._press_pos: QPoint | None = None
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    def set_language(self, lang: str) -> None:
        self._lang = lang
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def _was_quick_click(self, event) -> bool:
        if event.button() != Qt.MouseButton.LeftButton or self._press_pos is None:
            return False
        delta = event.globalPosition().toPoint() - self._press_pos
        self._press_pos = None
        return delta.manhattanLength() < 6


class ClockWidget(BaseCardWidget):
    """Widget đồng hồ lớn kính mờ."""

    def __init__(self, lang: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(340, 210, lang, parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        drawing.draw_card(
            p,
            self._card_width,
            self._card_height,
            CARD_RADIUS,
            (0.11, 0.14, 0.21, 0.94),
            (0.055, 0.07, 0.11, 0.96),
            0.18,
            hovered=self._hovered,
        )

        now = datetime.now()
        hours = f"{now.hour:02d}"
        minutes = f"{now.minute:02d}"

        size = 104
        font = drawing.make_font("SF Pro Rounded", size, QFont.Weight.DemiBold)
        fm = QFontMetricsF(font)
        hours_w = fm.horizontalAdvance(hours)
        mins_w = fm.horizontalAdvance(minutes)
        colon_w = round(size * 0.26)
        total_w = hours_w + colon_w + mins_w

        start_x = (self._card_width - total_w) / 2.0
        baseline_y = 128.0

        drawing.draw_glass_text(p, start_x, baseline_y, hours, size, "SF Pro Rounded", QFont.Weight.DemiBold)

        colon_x = start_x + hours_w + colon_w / 2.0
        colon_alpha = 0.90 if now.second % 2 == 0 else 0.38
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(drawing.rgba(0.96, 0.99, 1.0, colon_alpha))
        p.drawEllipse(QPointF(colon_x, baseline_y - 46), 4.6, 4.6)
        p.drawEllipse(QPointF(colon_x, baseline_y - 20), 4.6, 4.6)

        minutes_x = start_x + hours_w + colon_w
        drawing.draw_glass_text(p, minutes_x, baseline_y, minutes, size, "SF Pro Rounded", QFont.Weight.DemiBold)

        if self._lang == "vi":
            date_text = f"{WEEKDAYS[now.weekday()]}, {now.day:02d} tháng {now.month}, {now.year}"
        else:
            date_text = f"{EN_WEEKDAYS_LONG[now.weekday()]}, {EN_MONTHS_SHORT[now.month - 1]} {now.day}, {now.year}"

        drawing.draw_text(
            p,
            self._card_width / 2.0,
            174,
            date_text,
            13,
            drawing.COLORS["sysSub"],
            bold=False,
            align="center",
            family="SF Pro Display",
        )


class WeatherWidget(BaseCardWidget):
    """Widget thời tiết OpenWeatherMap / Open-Meteo."""

    _weather_loaded = pyqtSignal(object)

    def __init__(
        self,
        settings: WidgetSettings,
        icons_dir: Path,
        lang: str = "en",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(340, 210, lang, parent)
        self._settings = settings
        self._icons_dir = icons_dir
        self._data = WeatherData(
            city=settings.weather_city or ("Hà Nội" if lang == "vi" else "Hanoi"),
            date=tr(lang, "weather_loading"),
            temp="--",
            high="--",
            low="--",
            feels="--",
            humidity="--",
            wind="--",
            condition=tr(lang, "weather_connecting"),
            icon_path=None,
        )
        self.setToolTip(tr(lang, "weather_tip"))

        self._weather_loaded.connect(self._apply_weather)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_weather)
        self._restart_timer()
        self.refresh_weather()

    def set_language(self, lang: str) -> None:
        super().set_language(lang)
        self.setToolTip(tr(lang, "weather_tip"))
        self.refresh_weather()

    def _restart_timer(self) -> None:
        minutes = max(5, int(self._settings.weather_update_interval or 15))
        self._timer.start(minutes * 60 * 1000)

    def update_settings(self, settings: WidgetSettings) -> None:
        self._settings = settings
        self._restart_timer()
        self.refresh_weather()

    def refresh_weather(self) -> None:
        snapshot = self._settings
        icons_dir = self._icons_dir
        lang = self._lang

        def worker() -> None:
            result = fetch_weather(snapshot, icons_dir, lang=lang)
            self._weather_loaded.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_weather(self, data: WeatherData) -> None:
        self._data = data
        self.update()

    def on_quick_click(self) -> None:
        self.refresh_weather()

    def mouseReleaseEvent(self, event) -> None:
        if self._was_quick_click(event):
            self.on_quick_click()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        drawing.draw_card(
            p,
            self._card_width,
            self._card_height,
            CARD_RADIUS,
            (0.10, 0.30, 0.62, 0.97),
            (0.34, 0.63, 0.96, 0.97),
            0.20,
            hovered=self._hovered,
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(drawing.rgba(1.0, 1.0, 1.0, 0.08))
        p.drawEllipse(QPointF(self._card_width - 72, 64), 52, 52)

        d = self._data
        drawing.draw_text(p, 22, 36, d.city or "Hanoi", 17, drawing.COLORS["white"], True, "left", "SF Pro Display")
        drawing.draw_text(p, 22, 54, d.date, 11.5, drawing.COLORS["weatherSub"], False, "left")

        drawing.draw_text(p, 22, 116, f"{d.temp}°", 54, drawing.COLORS["white"], True, "left", "SF Pro Display")
        drawing.draw_text(p, 22, 138, d.condition, 13.5, drawing.COLORS["weatherSub"], False)

        drawing.draw_text(p, 22, 161, f"H:{d.high}°    L:{d.low}°", 12, drawing.COLORS["weatherSub"], False)
        drawing.draw_text(
            p,
            22,
            183,
            tr(self._lang, "weather_details", feels=d.feels, humidity=d.humidity, wind=d.wind),
            10.5,
            drawing.COLORS["weatherMuted"],
            False,
        )

        drawing.draw_svg_icon(p, d.icon_path, self._card_width - 120, 16, 96)


class SystemWidget(BaseCardWidget):
    """Widget giám sát CPU, GPU rời (nếu có), RAM, SSD và Mạng."""

    height_changed = pyqtSignal()

    def __init__(self, lang: str = "en", parent: QWidget | None = None) -> None:
        self._reader = SystemMetricsReader()
        self._metrics: SystemMetrics = self._reader.read()
        init_h = 300 if self._metrics.gpu.has_gpu else 258
        super().__init__(340, init_h, lang, parent)
        self.setToolTip(tr(lang, "system_tip"))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)

    def set_language(self, lang: str) -> None:
        super().set_language(lang)
        self.setToolTip(tr(lang, "system_tip"))

    def _refresh(self) -> None:
        self._metrics = self._reader.read()
        target_h = 300 if self._metrics.gpu.has_gpu else 258
        if self._card_height != target_h:
            self._card_height = target_h
            self.setFixedSize(self._card_width, target_h)
            self.height_changed.emit()
        self.update()

    def on_quick_click(self) -> None:
        _launch_first_available([
            ["plasma-systemmonitor"],
            ["ksysguard"],
            ["gnome-system-monitor"],
        ])

    def mouseReleaseEvent(self, event) -> None:
        if self._was_quick_click(event):
            self.on_quick_click()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        m = self._metrics
        has_gpu = m.gpu.has_gpu
        w = self._card_width
        h = self._card_height

        drawing.draw_card(
            p,
            w,
            h,
            CARD_RADIUS,
            (0.13, 0.13, 0.16, 0.95),
            (0.065, 0.065, 0.085, 0.97),
            0.15,
            hovered=self._hovered,
        )

        drawing.draw_text(
            p, 22, 36, tr(self._lang, "system_title"), 17, drawing.COLORS["sysText"], True, "left", "SF Pro Display"
        )
        drawing.draw_text(p, w - 22, 36, m.uptime, 11, drawing.COLORS["sysMuted"], False, "right")

        cpu_sub = m.cpu.model + (f"  •  {m.cpu.temp}°C" if m.cpu.temp is not None else "")
        drawing.draw_system_icon(p, "cpu", 22, 51, drawing.COLORS["blue"])
        drawing.draw_text(p, 44, 62, "CPU", 11.5, drawing.COLORS["sysSub"], False)
        drawing.draw_text(p, w - 22, 62, f"{m.cpu.percent}%", 12, drawing.COLORS["sysText"], True, "right")
        drawing.draw_progress_bar(p, 22, 69, w - 44, 6, m.cpu.percent, drawing.COLORS["blue"])
        drawing.draw_text(p, 22, 87, cpu_sub, 10, drawing.COLORS["sysMuted"], False)

        y_off = 94

        if has_gpu:
            gpu_val = f"{m.gpu.util}%"
            if m.gpu.temp is not None:
                gpu_val += f"  •  {m.gpu.temp}°C"
            gpu_sub = m.gpu.model or "GPU"
            if m.gpu.used and m.gpu.total:
                gpu_sub += f"  •  {m.gpu.used}/{m.gpu.total} MB"
            drawing.draw_system_icon(p, "gpu", 22, y_off, drawing.COLORS["green"])
            drawing.draw_text(p, 44, y_off + 11, "GPU", 11.5, drawing.COLORS["sysSub"], False)
            drawing.draw_text(p, w - 22, y_off + 11, gpu_val, 12, drawing.COLORS["sysText"], True, "right")
            drawing.draw_progress_bar(p, 22, y_off + 18, w - 44, 6, m.gpu.util, drawing.COLORS["green"])
            drawing.draw_text(p, 22, y_off + 36, gpu_sub, 10, drawing.COLORS["sysMuted"], False)
            y_off += 43

        ram_sub = f"{m.ram.text}  •  Swap {m.ram.swap_percent}%"
        drawing.draw_system_icon(p, "ram", 22, y_off, drawing.COLORS["purple"])
        drawing.draw_text(p, 44, y_off + 11, "RAM", 11.5, drawing.COLORS["sysSub"], False)
        drawing.draw_text(p, w - 22, y_off + 11, f"{m.ram.percent}%", 12, drawing.COLORS["sysText"], True, "right")
        drawing.draw_progress_bar(p, 22, y_off + 18, w - 44, 6, m.ram.percent, drawing.COLORS["purple"])
        drawing.draw_text(p, 22, y_off + 36, ram_sub, 10, drawing.COLORS["sysMuted"], False)
        y_off += 43

        drawing.draw_system_icon(p, "ssd", 22, y_off, drawing.COLORS["orange"])
        drawing.draw_text(p, 44, y_off + 11, "SSD", 11.5, drawing.COLORS["sysSub"], False)
        drawing.draw_text(p, w - 22, y_off + 11, f"{m.disk.percent}%", 12, drawing.COLORS["sysText"], True, "right")
        drawing.draw_progress_bar(p, 22, y_off + 18, w - 44, 6, m.disk.percent, drawing.COLORS["orange"])
        drawing.draw_text(p, 22, y_off + 36, m.disk.text, 10, drawing.COLORS["sysMuted"], False)
        y_off += 48

        p.setPen(drawing.rgba(1.0, 1.0, 1.0, 0.08))
        p.drawLine(22, y_off, w - 22, y_off)
        y_off += 10

        drawing.draw_system_icon(p, "network", 22, y_off, drawing.COLORS["cyan"])
        drawing.draw_text(p, 44, y_off + 11, tr(self._lang, "system_net"), 11.5, drawing.COLORS["sysSub"], False)
        drawing.draw_text(
            p,
            w - 22,
            y_off + 11,
            f"↓ {m.net.down_text}    ↑ {m.net.up_text}",
            11,
            drawing.COLORS["sysText"],
            True,
            "right",
        )
        drawing.draw_text(p, 22, y_off + 28, m.net.interface, 10, drawing.COLORS["sysMuted"], False)


class LunarWidget(BaseCardWidget):
    """Widget Âm lịch Việt Nam — luôn hiển thị bằng Tiếng Việt bất kể ngôn ngữ hệ thống."""

    def __init__(self, lang: str = "vi", parent: QWidget | None = None) -> None:
        # Cố định luôn hiển thị Tiếng Việt theo yêu cầu
        super().__init__(340, 150, "vi", parent)
        self._lunar = get_today_lunar()
        self.setToolTip("Kéo để di chuyển • Bấm nhanh để mở Lịch")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30 * 60 * 1000)

    def set_language(self, lang: str) -> None:
        # Âm lịch luôn giữ nguyên Tiếng Việt
        self._lang = "vi"
        self.update()

    def _refresh(self) -> None:
        self._lunar = get_today_lunar()
        self.update()

    def on_quick_click(self) -> None:
        _launch_first_available([
            ["am-lich-viet-nam"],
            ["korganizer"],
            ["gnome-calendar"],
        ])

    def mouseReleaseEvent(self, event) -> None:
        if self._was_quick_click(event):
            self.on_quick_click()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self._card_width
        h = self._card_height
        l = self._lunar

        drawing.draw_card(
            p,
            w,
            h,
            CARD_RADIUS,
            (0.19, 0.14, 0.31, 0.97),
            (0.075, 0.065, 0.12, 0.98),
            0.16,
            hovered=self._hovered,
        )

        drawing.draw_moon_watermark(p, w - 30, 39, 30)

        drawing.draw_text(p, 22, 34, "Âm lịch", 17, drawing.COLORS["sysText"], True, "left", "SF Pro Display")
        drawing.draw_text(p, w - 22, 34, "Hôm nay", 11, drawing.COLORS["sysMuted"], False, "right")

        drawing.draw_text(p, 22, 91, str(l.lunar_day), 48, drawing.COLORS["gold"], True, "left", "SF Pro Display")

        month_label = f"Tháng {l.lunar_month}{' nhuận' if l.lunar_leap else ''} · {l.year_name}"
        drawing.draw_text(p, 94, 65, month_label, 15, drawing.COLORS["sysText"], True, "left", "SF Pro Display")
        drawing.draw_text(p, 94, 84, f"Ngày {l.day_name} · Tháng {l.month_name}", 10.5, drawing.COLORS["sysSub"], False)

        p.setPen(drawing.rgba(1.0, 1.0, 1.0, 0.10))
        p.drawLine(22, 102, w - 22, 102)

        solar_str = f"{l.solar_day:02d}/{l.solar_month:02d}/{l.solar_year}  ·  {l.weekday}"
        drawing.draw_text(p, 22, 126, "Dương lịch", 10.5, drawing.COLORS["sysMuted"], False)
        drawing.draw_text(p, 94, 126, solar_str, 11.5, drawing.COLORS["sysSub"], False)


class RestWidget(BaseCardWidget):
    """Widget theo dõi thời gian hoạt động và nhắc nhở nghỉ ngơi (chu kỳ 50p/5p)."""

    def __init__(self, lang: str = "en", parent: QWidget | None = None) -> None:
        super().__init__(340, 165, lang, parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    @staticmethod
    def _format_clock(seconds: int) -> str:
        seconds = max(0, seconds)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self._card_width
        h = self._card_height
        uptime = read_uptime_seconds()
        cycle = int(uptime) % 3300
        on_break = cycle >= 3000

        if on_break:
            accent = drawing.COLORS["green"]
            top = (0.08, 0.34, 0.28, 0.97)
            bottom = (0.045, 0.15, 0.16, 0.98)
        elif cycle >= 2700:
            accent = drawing.COLORS["orange"]
            top = (0.39, 0.20, 0.10, 0.97)
            bottom = (0.17, 0.09, 0.08, 0.98)
        elif cycle >= 2100:
            accent = drawing.COLORS["gold"]
            top = (0.34, 0.27, 0.10, 0.97)
            bottom = (0.15, 0.12, 0.07, 0.98)
        else:
            accent = drawing.COLORS["cyan"]
            top = (0.10, 0.25, 0.38, 0.97)
            bottom = (0.055, 0.10, 0.18, 0.98)

        drawing.draw_card(p, w, h, CARD_RADIUS, top, bottom, 0.22, hovered=self._hovered)
        drawing.draw_rest_clock_watermark(p, w - 40, 42, 30)

        days = int(uptime // 86400)
        hours = int(uptime // 3600) % 24
        minutes = int(uptime // 60) % 60
        if days > 0:
            uptime_label = tr(self._lang, "rest_days_hours", days=days, hours=hours)
        elif hours > 0:
            uptime_label = f"{hours}h {minutes:02d}m"
        else:
            uptime_label = tr(self._lang, "rest_minutes", minutes=minutes)

        drawing.draw_text(
            p, 22, 34, tr(self._lang, "rest_title"), 17, drawing.COLORS["sysText"], True, "left", "SF Pro Display"
        )
        drawing.draw_text(p, 22, 68, uptime_label, 27, accent, True, "left", "SF Pro Display")
        drawing.draw_text(p, 22, 87, tr(self._lang, "rest_uptime_sub"), 11, drawing.COLORS["sysSub"], False)

        if on_break:
            remaining = 3300 - cycle
            progress = ((cycle - 3000) / 300.0) * 100.0
            status = tr(self._lang, "rest_break_status", time=self._format_clock(remaining))
            hint = tr(self._lang, "rest_break_hint")
        else:
            remaining = 3000 - cycle
            progress = (cycle / 3000.0) * 100.0
            status = tr(self._lang, "rest_work_status", time=self._format_clock(remaining))
            hint = (
                tr(self._lang, "rest_work_hint_soon")
                if cycle >= 2700
                else tr(self._lang, "rest_work_hint_normal")
            )

        drawing.draw_progress_bar(p, 22, 98, w - 44, 7, progress, accent)
        drawing.draw_text(p, 22, 125, status, 11.5, drawing.COLORS["sysText"], True)
        drawing.draw_text(p, 22, 145, hint, 10.5, drawing.COLORS["sysSub"], False)
