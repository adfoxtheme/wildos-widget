# WildOS Widget

Bộ widget màn hình desktop viết bằng **Python + PyQt6**, tối ưu cho **Wild OS / KDE Plasma (XWayland)** và hỗ trợ song ngữ **Tiếng Anh / Tiếng Việt**.

## Tính năng
- **5 widget độc lập kéo thả tự do & tự lưu vị trí:**
  - **Đồng hồ lớn (`ClockWidget`)**: số kính mờ `SF Pro Rounded`, nhấp nháy dấu `:`, ngày tháng theo ngôn ngữ hệ thống.
  - **Thời tiết (`WeatherWidget`)**: hỗ trợ OpenWeatherMap API Key hoặc fallback **Open-Meteo** miễn phí kèm bộ icon SVG.
  - **Hệ thống (`SystemWidget`)**: giám sát CPU (+ nhiệt độ), GPU rời NVIDIA/AMD (nếu có), RAM/Swap, SSD `/` và tốc độ mạng `↓ / ↑`.
  - **Âm lịch Việt Nam (`LunarWidget`)**: thuật toán Hồ Ngọc Đức (UTC+7), Can Chi năm/tháng/ngày, **luôn hiển thị bằng Tiếng Việt**.
  - **Nhắc nghỉ (`RestWidget`)**: theo dõi uptime theo chu kỳ 50 phút làm việc / 5 phút nghỉ.
- **Đường gióng thông minh & Hít từ tính (`Smart Guides`):** tự căn mép, lề viền màn hình (`24 px`) và khoảng cách chuẩn giữa các thẻ (`14 px`) khi kéo; giữ `Shift` để kéo tự do; dùng phím mũi tên để nhích `1 px` (`Shift + mũi tên` để nhích `10 px`).
- **Chạy ẩn ở khay hệ thống & Khởi động cùng OS:** icon khay đơn sắc tự đổi màu trắng/đen theo Dark/Light theme, hỗ trợ `--background` và `--toggle`.
- **Song ngữ Anh / Việt:** tự động theo ngôn ngữ hệ điều hành (Tiếng Việt khi OS là `vi_*`, Tiếng Anh cho các ngôn ngữ khác) hoặc chọn trực tiếp trong Cài đặt.

## Chạy và cài đặt
```bash
# Chạy trực tiếp
./launch.sh

# Chạy ẩn ở khay hệ thống (dùng cho autostart)
./launch.sh --background

# Bật/tắt bảng điều khiển
./launch.sh --toggle
```

## Kiểm thử
```bash
QT_QPA_PLATFORM=offscreen python3 test_app.py -v
```
