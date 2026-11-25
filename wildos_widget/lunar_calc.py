"""Thuật toán Âm lịch Việt Nam (Hồ Ngọc Đức, UTC+7)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

TIMEZONE = 7.0
SYNODIC_MONTH = 29.530588853

CAN = ("Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý")
CHI = ("Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi")
WEEKDAYS = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")


@dataclass(frozen=True)
class LunarInfo:
    lunar_day: int
    lunar_month: int
    lunar_year: int
    lunar_leap: bool
    year_name: str
    month_name: str
    day_name: str
    solar_day: int
    solar_month: int
    solar_year: int
    weekday: str


def _rad(deg: float) -> float:
    return (deg * math.pi) / 180.0


def jd_from_date(day: int, month: int, year: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (
        day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def _new_moon(k: int) -> float:
    t = k / 1236.85
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * t * t
    jd1 -= 0.000000155 * t * t * t
    jd1 += 0.00033 * math.sin(_rad(166.56 + 132.87 * t - 0.009173 * t * t))

    m = 359.2242 + 29.10535608 * k - 0.0000333 * t * t - 0.00000347 * t * t * t
    mpr = 306.0253 + 385.81691806 * k + 0.0107306 * t * t + 0.00001236 * t * t * t
    f = 21.2964 + 390.67050646 * k - 0.0016528 * t * t - 0.00000239 * t * t * t

    c1 = (0.1734 - 0.000393 * t) * math.sin(_rad(m))
    c1 += 0.0021 * math.sin(_rad(2 * m))
    c1 -= 0.4068 * math.sin(_rad(mpr))
    c1 += 0.0161 * math.sin(_rad(2 * mpr))
    c1 -= 0.0004 * math.sin(_rad(3 * mpr))
    c1 += 0.0104 * math.sin(_rad(2 * f))
    c1 -= 0.0051 * math.sin(_rad(m + mpr))
    c1 -= 0.0074 * math.sin(_rad(m - mpr))
    c1 += 0.0004 * math.sin(_rad(2 * f + m))
    c1 -= 0.0004 * math.sin(_rad(2 * f - m))
    c1 -= 0.0006 * math.sin(_rad(2 * f + mpr))
    c1 += 0.0010 * math.sin(_rad(2 * f - mpr))
    c1 += 0.0005 * math.sin(_rad(m + 2 * mpr))

    if t < -11:
        deltat = 0.001 + 0.000839 * t + 0.0002261 * t * t
        deltat -= 0.00000845 * t * t * t - 0.000000081 * t * t * t * t
    else:
        deltat = -0.000278 + 0.000265 * t + 0.000262 * t * t

    return jd1 + c1 - deltat


def _sun_longitude_degrees(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    m = 357.52910 + 35999.05030 * t - 0.0001559 * t * t - 0.00000048 * t * t * t
    l0 = 280.46645 + 36000.76983 * t + 0.0003032 * t * t
    dl = (1.914600 - 0.004817 * t - 0.000014 * t * t) * math.sin(_rad(m))
    dl += (0.019993 - 0.000101 * t) * math.sin(_rad(2 * m))
    dl += 0.000290 * math.sin(_rad(3 * m))
    lon = l0 + dl
    lon -= 360.0 * math.floor(lon / 360.0)
    return lon


def _new_moon_day(k: int, timezone: float = TIMEZONE) -> int:
    return math.floor(_new_moon(k) + 0.5 + timezone / 24.0)


def _sun_longitude_term(day: int, timezone: float = TIMEZONE) -> int:
    return math.floor(_sun_longitude_degrees(day - 0.5 - timezone / 24.0) / 30.0)


def _lunar_month_11(year: int, timezone: float = TIMEZONE) -> int:
    off = jd_from_date(31, 12, year) - 2415021
    k = math.floor(off / SYNODIC_MONTH)
    nm = _new_moon_day(k, timezone)
    if _sun_longitude_term(nm, timezone) >= 9:
        nm = _new_moon_day(k - 1, timezone)
    return nm


def _leap_month_offset(a11: int, timezone: float = TIMEZONE) -> int:
    k = math.floor((a11 - 2415021.076998695) / SYNODIC_MONTH + 0.5)
    last = 0
    i = 1
    arc = _sun_longitude_term(_new_moon_day(k + i, timezone), timezone)
    while arc != last and i < 14:
        last = arc
        i += 1
        arc = _sun_longitude_term(_new_moon_day(k + i, timezone), timezone)
    return i - 1


def convert_solar_to_lunar(
    day: int, month: int, year: int, timezone: float = TIMEZONE
) -> tuple[int, int, int, bool]:
    day_number = jd_from_date(day, month, year)
    k = math.floor((day_number - 2415021.076998695) / SYNODIC_MONTH)
    month_start = _new_moon_day(k + 1, timezone)
    if month_start > day_number:
        month_start = _new_moon_day(k, timezone)

    a11 = _lunar_month_11(year, timezone)
    b11 = a11
    if a11 >= month_start:
        lunar_year = year
        a11 = _lunar_month_11(year - 1, timezone)
    else:
        lunar_year = year + 1
        b11 = _lunar_month_11(year + 1, timezone)

    lunar_day = day_number - month_start + 1
    diff = math.floor((month_start - a11) / 29)
    leap = False
    lunar_month = diff + 11

    if b11 - a11 > 365:
        leap_month_diff = _leap_month_offset(a11, timezone)
        if diff >= leap_month_diff:
            lunar_month = diff + 10
            if diff == leap_month_diff:
                leap = True

    if lunar_month > 12:
        lunar_month -= 12
    if lunar_month >= 11 and diff < 4:
        lunar_year -= 1

    return int(lunar_day), int(lunar_month), int(lunar_year), leap


def can_chi_year(lunar_year: int) -> str:
    return f"{CAN[(lunar_year - 4) % 10]} {CHI[(lunar_year - 4) % 12]}"


def can_chi_month(lunar_year: int, lunar_month: int) -> str:
    year_can = (lunar_year - 4) % 10
    month_can = (year_can * 2 + lunar_month + 1) % 10
    month_chi = (lunar_month + 1) % 12
    return f"{CAN[month_can]} {CHI[month_chi]}"


def can_chi_day(day: int, month: int, year: int) -> str:
    jd = jd_from_date(day, month, year)
    return f"{CAN[(jd + 9) % 10]} {CHI[(jd + 1) % 12]}"


def get_today_lunar(now: datetime | None = None) -> LunarInfo:
    dt = now or datetime.now()
    lunar_day, lunar_month, lunar_year, leap = convert_solar_to_lunar(
        dt.day, dt.month, dt.year
    )
    return LunarInfo(
        lunar_day=lunar_day,
        lunar_month=lunar_month,
        lunar_year=lunar_year,
        lunar_leap=leap,
        year_name=can_chi_year(lunar_year),
        month_name=can_chi_month(lunar_year, lunar_month),
        day_name=can_chi_day(dt.day, dt.month, dt.year),
        solar_day=dt.day,
        solar_month=dt.month,
        solar_year=dt.year,
        weekday=WEEKDAYS[dt.weekday()],
    )
