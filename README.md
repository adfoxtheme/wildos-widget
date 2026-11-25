# WildOS Widget

A lightweight desktop widget suite built with **Python** and **PyQt6**, optimized for **Wild OS / KDE Plasma (XWayland)** with automatic **English / Vietnamese** localization.

The application appears in the desktop environment as **Widget**.

## Features
- **5 independent, freely draggable desktop widgets with persistent positions:**
  - **Large Clock (`ClockWidget`)**: frosted-glass `SF Pro Rounded` numerals, blinking `:` separator, and localized date display.
  - **Weather (`WeatherWidget`)**: supports an optional **OpenWeatherMap** API key or falls back to free **Open-Meteo** forecasts with bundled SVG weather icons.
  - **System Monitor (`SystemWidget`)**: tracks CPU usage and temperature, discrete NVIDIA/AMD GPU (if available), RAM/Swap, `/` SSD usage, and live network throughput (`↓ / ↑`).
  - **Vietnamese Lunar Calendar (`LunarWidget`)**: Hồ Ngọc Đức astronomical calculation (UTC+7) with Heavenly Stems & Earthly Branches (*Can Chi*) for year, month, and day (**always displayed in Vietnamese**).
  - **Rest Reminder (`RestWidget`)**: tracks system uptime in a 50-minute work / 5-minute break cycle.
- **Smart Alignment Guides & Magnetic Snapping (`Smart Guides`):** aligns widget edges, screen margins (`24 px`), and card spacing (`14 px`) while dragging; hold `Shift` for free placement; use arrow keys to nudge by `1 px` (`Shift + Arrow` for `10 px`).
- **System Tray & Autostart Support:** adaptive monochrome tray icon for Dark/Light themes with single-instance IPC and `--background`, `--toggle`, and `--toggle-widgets` flags.
- **Bilingual UI (English / Vietnamese):** automatically uses Vietnamese on `vi_*` locales and English otherwise, or can be configured directly in Settings.

## Requirements
- Python 3.10+
- PyQt6

## Usage
```bash
# Launch control panel & desktop widgets
./launch.sh

# Start hidden in the system tray (for autostart)
./launch.sh --background

# Toggle the control panel window
./launch.sh --toggle

# Toggle desktop widgets visibility
./launch.sh --toggle-widgets
```

## Testing
```bash
QT_QPA_PLATFORM=offscreen python3 test_app.py -v
```
