"""Dịch vụ lấy dữ liệu thời tiết (OpenWeatherMap và fallback Open-Meteo miễn phí)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .i18n import EN_MONTHS_SHORT, EN_WEEKDAYS_SHORT, resolve_language, tr
from .lunar_calc import WEEKDAYS
from .settings_store import WidgetSettings

# code: (vi_desc, en_desc, day_icon, night_icon)
WMO_CODES: dict[int, tuple[str, str, str, str]] = {
    0: ("Trời quang", "Clear sky", "weather-clear", "weather-clear-night"),
    1: ("Ít mây", "Mainly clear", "weather-few-clouds", "weather-few-clouds-night"),
    2: ("Có mây", "Partly cloudy", "weather-few-clouds", "weather-few-clouds-night"),
    3: ("Nhiều mây", "Overcast", "weather-overcast", "weather-overcast-night"),
    45: ("Sương mù", "Fog", "weather-fog", "weather-fog"),
    48: ("Sương mù", "Rime fog", "weather-fog", "weather-fog"),
    51: ("Mưa phùn nhẹ", "Light drizzle", "weather-showers-scattered", "weather-showers-scattered-night"),
    53: ("Mưa phùn", "Drizzle", "weather-showers", "weather-showers-night"),
    55: ("Mưa phùn dày", "Dense drizzle", "weather-showers", "weather-showers-night"),
    61: ("Mưa nhẹ", "Light rain", "weather-showers-scattered", "weather-showers-scattered-night"),
    63: ("Mưa vừa", "Moderate rain", "weather-showers", "weather-showers-night"),
    65: ("Mưa to", "Heavy rain", "weather-showers", "weather-showers-night"),
    71: ("Tuyết rơi nhẹ", "Light snow", "weather-snow-scattered", "weather-snow-scattered-night"),
    73: ("Tuyết rơi", "Snow", "weather-snow", "weather-snow-night"),
    75: ("Tuyết dày", "Heavy snow", "weather-snow", "weather-snow-night"),
    80: ("Mưa rào nhẹ", "Light showers", "weather-showers-scattered", "weather-showers-scattered-night"),
    81: ("Mưa rào", "Rain showers", "weather-showers", "weather-showers-night"),
    82: ("Mưa rào rất to", "Heavy showers", "weather-showers", "weather-showers-night"),
    95: ("Dông bão", "Thunderstorm", "weather-storm", "weather-storm-night"),
    96: ("Dông kèm mưa đá nhẹ", "Thunderstorm & hail", "weather-storm", "weather-storm-night"),
    99: ("Dông kèm mưa đá to", "Severe thunderstorm", "weather-storm", "weather-storm-night"),
}


@dataclass(frozen=True)
class WeatherData:
    city: str
    date: str
    temp: str
    high: str
    low: str
    feels: str
    humidity: str
    wind: str
    condition: str
    icon_path: str | None = None


def resolve_weather_icon(icon_name: str, icons_dir: Path) -> str | None:
    """Tìm file SVG tương ứng trong thư mục weather-icons, có fallback hợp lý."""
    candidates = [
        icon_name,
        icon_name.replace("-night", ""),
        "weather-storm" if "storm" in icon_name else "",
        "weather-severe-alert" if "storm" in icon_name else "",
        "weather-few-clouds",
    ]
    for name in candidates:
        if not name:
            continue
        p = icons_dir / f"{name}.svg"
        if p.exists():
            return str(p)
    return None


def _map_openweather_icon(icon_code: str, condition_id: int) -> str:
    is_night = bool(icon_code and icon_code.endswith("n"))
    if 200 <= condition_id < 300:
        return "weather-storm-night" if is_night else "weather-storm"
    if 300 <= condition_id < 400:
        return "weather-showers-scattered-night" if is_night else "weather-showers-scattered"
    if 500 <= condition_id < 600:
        if condition_id == 511:
            return "weather-freezing-rain"
        return "weather-showers-night" if is_night else "weather-showers"
    if 600 <= condition_id < 700:
        return "weather-snow-night" if is_night else "weather-snow"
    if 700 <= condition_id < 800:
        return "weather-fog"
    if condition_id == 800:
        return "weather-clear-night" if is_night else "weather-clear"
    if condition_id in (801, 802):
        return "weather-few-clouds-night" if is_night else "weather-few-clouds"
    return "weather-overcast-night" if is_night else "weather-overcast"


def _http_get_json(url: str, timeout: int = 8) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "WildOSWidget/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode_city(city: str, lang: str) -> tuple[float, float, str] | None:
    try:
        q = urllib.parse.quote(city)
        data = _http_get_json(
            f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language={lang}&format=json",
            timeout=5,
        )
        results = data.get("results") or []
        if results:
            r = results[0]
            return float(r["latitude"]), float(r["longitude"]), str(r.get("name") or city)
    except Exception:
        pass
    return None


def _format_weather_date(now: datetime, lang: str) -> str:
    if lang == "vi":
        return f"{WEEKDAYS[now.weekday()]}, {now.day}/{now.month}"
    return f"{EN_WEEKDAYS_SHORT[now.weekday()]}, {EN_MONTHS_SHORT[now.month - 1]} {now.day}"


def fetch_weather(settings: WidgetSettings, icons_dir: Path, lang: str | None = None) -> WeatherData:
    active_lang = resolve_language(lang or settings.language)
    api_key = settings.weather_api_key.strip()
    city = (settings.weather_city or ("Hà Nội" if active_lang == "vi" else "Hanoi")).strip()
    lat = settings.weather_lat
    lon = settings.weather_lon

    now = datetime.now()
    date_label = _format_weather_date(now, active_lang)

    if api_key:
        try:
            q_city = urllib.parse.quote(city)
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={q_city}&appid={api_key}&units=metric&lang={active_lang}"
            )
            data = _http_get_json(url)
            main = data["main"]
            condition = "Trời quang" if active_lang == "vi" else "Clear sky"
            icon_name = "weather-clear"
            weather_list = data.get("weather") or []
            if weather_list:
                w = weather_list[0]
                desc = str(w.get("description") or condition)
                condition = desc[0].upper() + desc[1:] if desc else condition
                icon_name = _map_openweather_icon(str(w.get("icon") or ""), int(w.get("id") or 800))

            return WeatherData(
                city=str(data.get("name") or city),
                date=date_label,
                temp=str(round(main["temp"])),
                high=str(round(main["temp_max"])),
                low=str(round(main["temp_min"])),
                feels=str(round(main["feels_like"])),
                humidity=str(round(main["humidity"])),
                wind=str(round(data["wind"]["speed"] * 3.6)),
                condition=condition,
                icon_path=resolve_weather_icon(icon_name, icons_dir),
            )
        except Exception:
            pass

    if city and city.lower() not in ("hà nội", "ha noi", "hanoi"):
        geo = _geocode_city(city, active_lang)
        if geo:
            lat, lon, resolved_name = geo
            city = resolved_name

    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        )
        data = _http_get_json(url)
        current = data["current"]
        daily = data.get("daily") or {}
        highs = daily.get("temperature_2m_max") or []
        lows = daily.get("temperature_2m_min") or []

        code = int(current.get("weather_code") or 0)
        is_night = now.hour < 6 or now.hour >= 18
        default_entry = (
            "Thời tiết tốt" if active_lang == "vi" else "Fair",
            "Fair",
            "weather-few-clouds",
            "weather-few-clouds-night",
        )
        entry = WMO_CODES.get(code, default_entry)
        condition = entry[0] if active_lang == "vi" else entry[1]
        icon_name = entry[3] if is_night else entry[2]

        return WeatherData(
            city=city,
            date=date_label,
            temp=str(round(current["temperature_2m"])),
            high=str(round(highs[0])) if highs else "--",
            low=str(round(lows[0])) if lows else "--",
            feels=str(round(current["apparent_temperature"])),
            humidity=str(round(current["relative_humidity_2m"])),
            wind=str(round(current["wind_speed_10m"])),
            condition=condition,
            icon_path=resolve_weather_icon(icon_name, icons_dir),
        )
    except Exception:
        return WeatherData(
            city=city,
            date=date_label,
            temp="--",
            high="--",
            low="--",
            feels="--",
            humidity="--",
            wind="--",
            condition=tr(active_lang, "weather_offline"),
            icon_path=resolve_weather_icon("weather-few-clouds", icons_dir),
        )
