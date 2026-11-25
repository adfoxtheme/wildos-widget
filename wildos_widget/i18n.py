"""Hỗ trợ đa ngôn ngữ (Tiếng Anh mặc định cho OS ngoài Việt Nam, Tiếng Việt khi OS/người dùng chọn vi)."""

from __future__ import annotations

import os

from PyQt6.QtCore import QLocale

EN_WEEKDAYS_LONG = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
EN_WEEKDAYS_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
EN_MONTHS_SHORT = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

VI_WEEKDAYS_SHORT = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")

STRINGS: dict[str, dict[str, str]] = {
    "vi": {
        "app_name": "Widget",
        "panel_title": "Widget — Bảng điều khiển",
        "panel_subtitle": "Kéo từng thẻ widget ra ngoài màn hình hoặc bật công tắc để đặt lên desktop",
        "settings_title": "Cài đặt Widget",
        "btn_show_all_on": "Đang hiện",
        "btn_show_all_off": "Đang ẩn hết",
        "btn_snap_on": "Căn gióng",
        "btn_snap_off": "Tắt gióng",
        "btn_snap_tip": "Hiện đường gióng & hít khoảng cách đều khi kéo (giữ Shift để kéo tự do)",
        "btn_lock_on": "Đã khóa",
        "btn_lock_off": "Khóa vị trí",
        "btn_settings": "Cài đặt",
        "btn_reset": "Xếp mặc định",
        "btn_hide_tray": "Thu xuống khay",
        "chk_autostart": "Chạy ẩn ở khay hệ thống cùng OS",
        "row_drag_tip": "Nhấn giữ và kéo ra ngoài cửa sổ để thả widget lên màn hình",
        "row_on": "Đang bật",
        "row_off": "Đang tắt",
        "row_pos_shown": "Trên màn hình tại ({x}, {y}) · Kéo để đặt lại",
        "row_pos_hidden": "Đã lưu vị trí ({x}, {y}) · Đang tạm ẩn",
        "row_pos_off": "Kéo thẻ này ra màn hình hoặc bấm Đang tắt để bật",
        # Widget catalog
        "cat_clock_title": "Đồng hồ lớn",
        "cat_clock_desc": "Số kính mờ SF Pro Rounded + ngày tháng",
        "cat_weather_title": "Thời tiết",
        "cat_weather_desc": "Dự báo thời tiết OpenWeatherMap / Open-Meteo",
        "cat_system_title": "Hệ thống",
        "cat_system_desc": "CPU, GPU, RAM, SSD và tốc độ mạng",
        "cat_lunar_title": "Âm lịch Việt Nam",
        "cat_lunar_desc": "Ngày âm lịch, Can Chi và ngày Dương lịch (luôn tiếng Việt)",
        "cat_rest_title": "Nhắc nghỉ ngơi",
        "cat_rest_desc": "Đếm ngược chu kỳ 50p làm việc / 5p nghỉ",
        # Settings dialog
        "grp_weather": "Thời tiết (để trống API Key sẽ dùng Open-Meteo miễn phí)",
        "lbl_api_key": "OpenWeather API Key:",
        "ph_api_key": "Tùy chọn — OpenWeatherMap API Key",
        "lbl_city": "Tên thành phố:",
        "ph_city": "Ví dụ: Hà Nội, Đà Nẵng, TP Hồ Chí Minh",
        "lbl_lat": "Vĩ độ (mặc định):",
        "lbl_lon": "Kinh độ (mặc định):",
        "lbl_interval": "Chu kỳ cập nhật:",
        "suffix_minutes": " phút",
        "grp_system": "Hiển thị, Ngôn ngữ & Khởi động cùng OS",
        "lbl_lang": "Ngôn ngữ giao diện:",
        "lang_auto": "Tự động theo hệ thống (OS)",
        "lang_vi": "Tiếng Việt",
        "lang_en": "English",
        "lbl_layer": "Lớp hiển thị widget trên màn hình:",
        "layer_bottom": "Ghim dưới các cửa sổ (như widget nền)",
        "layer_normal": "Cửa sổ bình thường",
        "layer_top": "Luôn nổi trên cùng",
        "lbl_gap": "Khoảng cách chuẩn giữa các widget:",
        "lbl_margin": "Lề viền màn hình:",
        "chk_snap": "Hiện đường gióng & tự hít căn chỉnh khi kéo widget",
        "chk_lock": "Khóa vị trí widget (tránh kéo nhầm khi bấm)",
        "chk_keep_tray": "Chạy ẩn dưới khay hệ thống khi đóng bảng điều khiển",
        "chk_autostart_full": "Tự khởi động ẩn ở khay hệ thống khi mở máy cùng OS",
        "btn_save": "Lưu",
        "btn_cancel": "Hủy",
        # Context & tray menus
        "close_widget_tip": "Ẩn widget này khỏi màn hình",
        "menu_unlock": "Mở khóa vị trí",
        "menu_lock": "Khóa vị trí widget",
        "menu_snap": "Hít & Đường gióng khi kéo",
        "menu_reset": "Xếp lại vị trí mặc định",
        "menu_hide_widget": "Ẩn widget này",
        "menu_open_panel": "Mở Bảng điều khiển…",
        "menu_refresh_weather": "Làm mới thời tiết",
        "menu_settings": "Cài đặt…",
        "menu_quit": "Thoát hẳn",
        "tray_tip": "Widget — Bấm để ẩn/hiện",
        "tray_toggle_widgets": "Hiện / Ẩn các Widget",
        "tray_toggle_lock": "Khóa / Mở khóa vị trí",
        # Widget internal texts
        "weather_tip": "Kéo để di chuyển • Bấm nhanh để cập nhật thời tiết",
        "weather_loading": "Đang tải…",
        "weather_connecting": "Đang kết nối…",
        "weather_offline": "Chưa có mạng",
        "weather_details": "Cảm giác {feels}°  •  Độ ẩm {humidity}%  •  Gió {wind} km/h",
        "system_title": "Hệ thống",
        "system_net": "Mạng",
        "system_tip": "Kéo để di chuyển • Bấm nhanh để mở Trình quản lý tác vụ",
        "rest_title": "Nhắc nghỉ",
        "rest_uptime_sub": "Máy hoạt động",
        "rest_days_hours": "{days} ngày {hours}h",
        "rest_minutes": "{minutes} phút",
        "rest_break_status": "Nghỉ ngắn · còn {time}",
        "rest_break_hint": "Đi lại nhẹ nhàng, rời màn hình.",
        "rest_work_status": "Còn {time} đến giờ nghỉ",
        "rest_work_hint_soon": "Sắp đến lúc đứng dậy, vươn vai.",
        "rest_work_hint_normal": "Đổi tư thế, chớp mắt và nhìn xa.",
    },
    "en": {
        "app_name": "Widget",
        "panel_title": "Widget — Control Panel",
        "panel_subtitle": "Drag any widget card onto your screen or toggle switches to place on desktop",
        "settings_title": "Widget Settings",
        "btn_show_all_on": "Showing",
        "btn_show_all_off": "Hidden",
        "btn_snap_on": "Snap Guides",
        "btn_snap_off": "Snap Off",
        "btn_snap_tip": "Show alignment guides & magnetic snap while dragging (hold Shift for free move)",
        "btn_lock_on": "Locked",
        "btn_lock_off": "Lock Position",
        "btn_settings": "Settings",
        "btn_reset": "Reset Layout",
        "btn_hide_tray": "Hide to Tray",
        "chk_autostart": "Run hidden in system tray on OS startup",
        "row_drag_tip": "Press and drag outside this window to drop the widget onto your desktop",
        "row_on": "Enabled",
        "row_off": "Disabled",
        "row_pos_shown": "On screen at ({x}, {y}) · Drag to reposition",
        "row_pos_hidden": "Saved at ({x}, {y}) · Temporarily hidden",
        "row_pos_off": "Drag this card onto screen or click Disabled to enable",
        # Widget catalog
        "cat_clock_title": "Large Clock",
        "cat_clock_desc": "Frosted glass SF Pro Rounded numerals + date",
        "cat_weather_title": "Weather",
        "cat_weather_desc": "Weather forecast via OpenWeatherMap / Open-Meteo",
        "cat_system_title": "System Monitor",
        "cat_system_desc": "CPU, GPU, RAM, SSD and network speed",
        "cat_lunar_title": "Vietnamese Lunar Calendar",
        "cat_lunar_desc": "Lunar date, Can Chi and Solar date (always in Vietnamese)",
        "cat_rest_title": "Rest Reminder",
        "cat_rest_desc": "50m work / 5m break cycle countdown",
        # Settings dialog
        "grp_weather": "Weather (leave API Key blank to use free Open-Meteo)",
        "lbl_api_key": "OpenWeather API Key:",
        "ph_api_key": "Optional — OpenWeatherMap API Key",
        "lbl_city": "City name:",
        "ph_city": "e.g. Hanoi, London, Tokyo",
        "lbl_lat": "Latitude (default):",
        "lbl_lon": "Longitude (default):",
        "lbl_interval": "Update interval:",
        "suffix_minutes": " min",
        "grp_system": "Display, Language & OS Startup",
        "lbl_lang": "Interface language:",
        "lang_auto": "Auto (Follow OS)",
        "lang_vi": "Tiếng Việt",
        "lang_en": "English",
        "lbl_layer": "Desktop widget layer:",
        "layer_bottom": "Pin below windows (desktop background)",
        "layer_normal": "Normal window",
        "layer_top": "Always on top",
        "lbl_gap": "Standard gap between widgets:",
        "lbl_margin": "Screen edge margin:",
        "chk_snap": "Show smart guides & magnetic snap while dragging",
        "chk_lock": "Lock widget positions (prevent accidental dragging)",
        "chk_keep_tray": "Keep running in system tray when closing control panel",
        "chk_autostart_full": "Start hidden in system tray on OS login",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        # Context & tray menus
        "close_widget_tip": "Hide this widget from screen",
        "menu_unlock": "Unlock position",
        "menu_lock": "Lock widget position",
        "menu_snap": "Snap & smart guides",
        "menu_reset": "Reset default layout",
        "menu_hide_widget": "Hide this widget",
        "menu_open_panel": "Open Control Panel…",
        "menu_refresh_weather": "Refresh weather",
        "menu_settings": "Settings…",
        "menu_quit": "Quit",
        "tray_tip": "Widget — Click to show/hide",
        "tray_toggle_widgets": "Show / Hide Widgets",
        "tray_toggle_lock": "Lock / Unlock Positions",
        # Widget internal texts
        "weather_tip": "Drag to move • Quick click to refresh weather",
        "weather_loading": "Loading…",
        "weather_connecting": "Connecting…",
        "weather_offline": "No internet",
        "weather_details": "Feels {feels}°  •  Humidity {humidity}%  •  Wind {wind} km/h",
        "system_title": "System",
        "system_net": "Network",
        "system_tip": "Drag to move • Quick click to open System Monitor",
        "rest_title": "Rest Reminder",
        "rest_uptime_sub": "System uptime",
        "rest_days_hours": "{days}d {hours}h",
        "rest_minutes": "{minutes} min",
        "rest_break_status": "Break time · {time} left",
        "rest_break_hint": "Stretch gently, look away from screen.",
        "rest_work_status": "{time} until next break",
        "rest_work_hint_soon": "Almost time to stand up and stretch.",
        "rest_work_hint_normal": "Change posture, blink, and look far.",
    },
}


def detect_os_language() -> str:
    """Phát hiện ngôn ngữ OS: trả về 'vi' nếu tiếng Việt, ngược lại mặc định 'en'."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        val = (os.environ.get(var) or "").strip().lower()
        if not val:
            continue
        first = val.split(":")[0]
        if first.startswith("vi"):
            return "vi"
        if first and first not in ("c", "c.utf-8", "posix"):
            return "en"

    try:
        locale = QLocale.system()
        if locale.language() == QLocale.Language.Vietnamese or locale.name().lower().startswith("vi"):
            return "vi"
    except Exception:
        pass
    return "en"


def resolve_language(pref: str | None) -> str:
    if pref == "vi":
        return "vi"
    if pref == "en":
        return "en"
    return detect_os_language()


def tr(lang: str, key: str, **kwargs) -> str:
    table = STRINGS.get(lang, STRINGS["en"])
    text = table.get(key) or STRINGS["en"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
