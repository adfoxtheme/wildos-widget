"""Quản lý cấu hình JSON và tự khởi động cùng hệ điều hành cho WildOS Widget."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

WIDGET_IDS = ("clock", "weather", "system", "lunar", "rest")

DEFAULT_POSITIONS: dict[str, list[int]] = {
    "clock": [80, 80],
    "weather": [1160, 80],
    "system": [1160, 304],
    "lunar": [1160, 618],
    "rest": [1160, 782],
}


@dataclass
class WidgetSettings:
    show_clock: bool = True
    show_weather: bool = True
    show_system: bool = True
    show_lunar: bool = True
    show_rest: bool = True

    widgets_visible: bool = True
    lock_positions: bool = False
    snap_enabled: bool = True
    snap_gap: int = 14
    snap_margin: int = 24
    widget_layer: str = "bottom"  # "bottom" | "normal" | "top"

    positions: dict[str, list[int]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_POSITIONS.items()}
    )

    weather_api_key: str = ""
    weather_city: str = "Hà Nội"
    weather_lat: float = 21.0285
    weather_lon: float = 105.8542
    weather_update_interval: int = 15

    keep_in_tray: bool = True
    autostart: bool = False
    language: str = "auto"  # "auto" | "en" | "vi"


class SettingsStore:
    """Đọc và lưu cấu hình ứng dụng ra ~/.config/wildos-widget/settings.json."""

    def __init__(
        self,
        path: Path | None = None,
        autostart_path: Path | None = None,
    ) -> None:
        self.path = path or (Path.home() / ".config" / "wildos-widget" / "settings.json")
        self.autostart_path = autostart_path or (
            Path.home() / ".config" / "autostart" / "vn.ihoan.WildOSWidget.desktop"
        )
        self.settings = self.load()

    def load(self) -> WidgetSettings:
        defaults = WidgetSettings()
        if not self.path.exists():
            return defaults
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return defaults
            data = asdict(defaults)
            for key, val in raw.items():
                if key == "positions" and isinstance(val, dict):
                    merged = {k: list(v) for k, v in DEFAULT_POSITIONS.items()}
                    for wk, wpos in val.items():
                        if wk in merged and isinstance(wpos, list) and len(wpos) == 2:
                            merged[wk] = [int(wpos[0]), int(wpos[1])]
                    data["positions"] = merged
                elif key in data:
                    data[key] = val
            return WidgetSettings(**data)
        except Exception:
            return defaults

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(self.settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_widget_enabled(self, widget_id: str) -> bool:
        return bool(getattr(self.settings, f"show_{widget_id}", False))

    def set_widget_enabled(self, widget_id: str, enabled: bool) -> None:
        if widget_id in WIDGET_IDS:
            setattr(self.settings, f"show_{widget_id}", bool(enabled))

    def get_position(self, widget_id: str) -> tuple[int, int]:
        pos = self.settings.positions.get(widget_id) or DEFAULT_POSITIONS.get(widget_id, [100, 100])
        return int(pos[0]), int(pos[1])

    def set_position(self, widget_id: str, x: int, y: int) -> None:
        if widget_id in WIDGET_IDS:
            self.settings.positions[widget_id] = [int(x), int(y)]

    def sync_autostart(self, exec_cmd: str = "/home/ihoan/.local/bin/wildos-widget --background") -> None:
        """Tạo hoặc xóa file ~/.config/autostart/vn.ihoan.WildOSWidget.desktop."""
        if self.settings.autostart:
            self.autostart_path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Widget\n"
                "Comment=Tự khởi động widget ở khay hệ thống\n"
                f"Exec={exec_cmd}\n"
                "Icon=vn.ihoan.WildOSWidget\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "X-KDE-autostart-after=panel\n"
            )
            self.autostart_path.write_text(content, encoding="utf-8")
        else:
            try:
                self.autostart_path.unlink(missing_ok=True)
            except OSError:
                pass
