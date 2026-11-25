"""Kiểm thử tự động cho các module logic, widget nổi độc lập, kéo thả, lưu vị trí và autostart."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SCRATCH_DIR = Path(__file__).resolve().parent
if str(SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(SCRATCH_DIR))

from PyQt6.QtWidgets import QApplication

from tahoe_widgets.drawing import build_symbolic_tray_icon
from tahoe_widgets.i18n import detect_os_language, resolve_language, tr
from tahoe_widgets.lunar_calc import convert_solar_to_lunar, get_today_lunar
from tahoe_widgets.main_window import SettingsDialog, TahoeControlWindow
from tahoe_widgets.manager import DesktopWidgetManager
from tahoe_widgets.settings_store import SettingsStore
from tahoe_widgets.snap_engine import Rect, compute_snap
from tahoe_widgets.snap_overlay import SnapGuideOverlay
from tahoe_widgets.system_metrics import SystemMetricsReader


class TahoeWidgetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["test"])

    def test_lunar_tet_2026(self) -> None:
        day, month, year, leap = convert_solar_to_lunar(17, 2, 2026)
        self.assertEqual((day, month, year, leap), (1, 1, 2026, False))
        info = get_today_lunar(datetime(2026, 2, 17))
        self.assertEqual(info.year_name, "Bính Ngọ")

    def test_settings_positions_and_autostart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = tmp_path / "settings.json"
            auto = tmp_path / "autostart" / "vn.ihoan.TahoeWidgets.desktop"

            store = SettingsStore(cfg, auto)
            store.set_position("clock", 123, 456)
            store.settings.autostart = True
            store.settings.weather_city = "Đà Nẵng"
            store.save()
            store.sync_autostart()

            self.assertTrue(auto.exists())
            self.assertIn("--background", auto.read_text(encoding="utf-8"))

            reloaded = SettingsStore(cfg, auto)
            self.assertEqual(reloaded.get_position("clock"), (123, 456))
            self.assertEqual(reloaded.settings.weather_city, "Đà Nẵng")
            self.assertTrue(reloaded.settings.autostart)

            reloaded.settings.autostart = False
            reloaded.sync_autostart()
            self.assertFalse(auto.exists())

    def test_system_metrics_reader(self) -> None:
        reader = SystemMetricsReader()
        m1 = reader.read()
        m2 = reader.read()
        self.assertGreaterEqual(m2.cpu.percent, 0)
        self.assertLessEqual(m2.cpu.percent, 100)
        self.assertIn("GiB", m2.ram.text)
        self.assertIn("GiB", m2.disk.text)
        self.assertRegex(m1.uptime, r"^\d{2,}:\d{2}:\d{2}$")

    def test_desktop_widgets_and_control_panel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = SettingsStore(
                tmp_path / "settings.json",
                tmp_path / "autostart" / "vn.ihoan.TahoeWidgets.desktop",
            )
            assets_dir = tmp_path / "assets"
            (assets_dir / "weather-icons").mkdir(parents=True)

            manager = DesktopWidgetManager(store, assets_dir)
            manager.sync_all()
            self.app.processEvents()

            for wid in ("clock", "weather", "system", "lunar", "rest"):
                win = manager._windows.get(wid)
                self.assertIsNotNone(win)
                self.assertTrue(win.isVisible())
                pix = win.card.grab()
                self.assertFalse(pix.isNull())

            # Test drag-drop placement saves coordinates (tắt snap để kiểm tra tọa độ tuyệt đối)
            manager.set_snap_enabled(False)
            manager.place_widget_at("lunar", 250, 320)
            self.assertEqual(store.get_position("lunar"), (250, 320))
            manager.set_snap_enabled(True)

            # Test hiding a single widget
            manager.hide_single_widget("rest")
            self.assertFalse(store.is_widget_enabled("rest"))
            self.assertFalse(manager._windows["rest"].isVisible())

            # Test hiding all widgets & control panel UI
            panel = TahoeControlWindow(store, manager, assets_dir, tray_available=True)
            panel.show()
            manager.toggle_all_visible()
            self.assertFalse(store.settings.widgets_visible)
            self.assertFalse(manager._windows["clock"].isVisible())

            dlg = SettingsDialog(store.settings, panel)
            dlg.show()
            self.app.processEvents()
            for ctrl in (
                dlg.cb_lang,
                dlg.cb_layer,
                dlg.sp_gap,
                dlg.sp_margin,
                dlg.ed_city,
                dlg.ed_api_key,
                dlg.sp_interval,
                dlg.sp_lat,
                dlg.sp_lon,
            ):
                self.assertEqual(ctrl.width(), SettingsDialog.CONTROL_WIDTH)
                self.assertEqual(ctrl.height(), SettingsDialog.CONTROL_HEIGHT)
            self.assertFalse(dlg.grab().isNull())
            dlg.chk_autostart.setChecked(True)
            dlg.apply_to(store.settings)
            self.assertTrue(store.settings.autostart)
            dlg.close()

            manager.close_all()
            panel.close()

    def test_symbolic_tray_icon_tinting(self) -> None:
        svg_path = SCRATCH_DIR / "vn.ihoan.TahoeWidgets-symbolic.svg"
        if not svg_path.exists():
            svg_path = SCRATCH_DIR / "assets" / "vn.ihoan.TahoeWidgets-symbolic.svg"
        self.assertTrue(svg_path.exists())
        dark_icon = build_symbolic_tray_icon(svg_path, "#eff0f1")
        light_icon = build_symbolic_tray_icon(svg_path, "#232629")
        self.assertFalse(dark_icon.pixmap(22, 22).isNull())
        self.assertFalse(light_icon.pixmap(22, 22).isNull())

    def test_smart_snap_and_overlay(self) -> None:
        screen = Rect(0, 0, 1920, 1080)
        # Card bên trên: đặt cách lề phải 24px (x = 1920 - 24 - 340 = 1556), y = 24, h = 210
        top_card = Rect(1556, 24, 340, 210)
        # Kéo card thứ hai gần vị trí thẳng hàng và cách dưới 14px (y chuẩn = 24 + 210 + 14 = 248)
        moving = Rect(1551, 253, 340, 258)
        res = compute_snap(moving, [top_card], screen, threshold=10, edge_margin=24, card_gap=14)
        self.assertEqual((res.x, res.y), (1556, 248))
        self.assertTrue(any(b.label == "14 px" for b in res.badges))
        self.assertTrue(any(g.orientation == "v" for g in res.guides))

        # Test lề trái màn hình 24px
        left_moving = Rect(19, 28, 340, 210)
        res_left = compute_snap(left_moving, [], screen, threshold=10, edge_margin=24, card_gap=14)
        self.assertEqual((res_left.x, res_left.y), (24, 24))
        self.assertTrue(any(b.label == "24 px" for b in res_left.badges))

        # Test render SnapGuideOverlay
        overlay = SnapGuideOverlay()
        overlay.show_guides((0, 0, 1920, 1080), res.guides, res.badges)
        self.app.processEvents()
        pix = overlay.grab()
        self.assertFalse(pix.isNull())
        overlay.clear_and_hide()
        overlay.close()

    def test_i18n_and_lunar_always_vietnamese(self) -> None:
        old_env = {k: os.environ.get(k) for k in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        try:
            for k in old_env:
                os.environ.pop(k, None)
            os.environ["LANG"] = "vi_VN.UTF-8"
            self.assertEqual(detect_os_language(), "vi")
            os.environ["LANG"] = "en_US.UTF-8"
            self.assertEqual(detect_os_language(), "en")
            os.environ["LANG"] = "ja_JP.UTF-8"
            self.assertEqual(detect_os_language(), "en")
            os.environ["LANG"] = "fr_FR.UTF-8"
            self.assertEqual(detect_os_language(), "en")
            self.assertEqual(resolve_language("vi"), "vi")
            self.assertEqual(resolve_language("en"), "en")
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = SettingsStore(tmp_path / "settings.json", tmp_path / "auto.desktop")
            store.settings.language = "en"
            assets_dir = tmp_path / "assets"
            (assets_dir / "weather-icons").mkdir(parents=True)

            manager = DesktopWidgetManager(store, assets_dir)
            manager.sync_all()
            panel = TahoeControlWindow(store, manager, assets_dir, tray_available=True)
            self.assertEqual(panel.windowTitle(), tr("en", "panel_title"))

            # Lunar widget must stay Vietnamese even in English mode
            lunar_win = manager._windows["lunar"]
            self.assertEqual(lunar_win.card._lang, "vi")
            lunar_win.set_language("en")
            self.assertEqual(lunar_win.card._lang, "vi")

            # Switch to Vietnamese
            store.settings.language = "vi"
            manager.refresh_language()
            self.assertEqual(panel.windowTitle(), tr("vi", "panel_title"))
            self.assertEqual(manager._windows["rest"].card._lang, "vi")

            manager.close_all()
            panel.close()


if __name__ == "__main__":
    unittest.main()
