#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PACKAGE_NAME="wildos-widget"
VERSION="1.0.1"
BUILD_DIR="${SCRIPT_DIR}/build/deb"
OUTPUT_DEB="${SCRIPT_DIR}/${PACKAGE_NAME}_${VERSION}_all.deb"

echo "==> Preparing build directory: ${BUILD_DIR}"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
chmod 755 "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"

# Launcher
cat << 'EOF' > "${BUILD_DIR}/usr/bin/wildos-widget"
#!/usr/bin/env bash
# WildOS Widget launcher
exec python3 /usr/lib/wildos-widget/main.py "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/wildos-widget"

# App & Assets
cp -a "${SCRIPT_DIR}/main.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp -a "${SCRIPT_DIR}/wildos_widget" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
find "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/wildos_widget" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

cp -a "${SCRIPT_DIR}/assets" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
rm -rf "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/assets/screenshots"

# Desktop & Icon
cp -a "${SCRIPT_DIR}/vn.ihoan.WildOSWidget.desktop" "${BUILD_DIR}/usr/share/applications/"
cp -a "${SCRIPT_DIR}/assets/vn.ihoan.WildOSWidget.svg" "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/"

# Control metadata
INSTALLED_SIZE=$(du -sk --exclude=DEBIAN "${BUILD_DIR}" | awk '{print $1}')

cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt6
Recommends: python3-requests
Suggests: python3-psutil
Installed-Size: ${INSTALLED_SIZE}
Maintainer: ihoan <vn.ihoan@gmail.com>
Homepage: https://github.com/adfoxtheme/wildos-widget
Description: Desktop widget suite for Wild OS / KDE Plasma
 WildOS Widget is a lightweight desktop widget suite built with Python
 and PyQt6, optimized for Wild OS / KDE Plasma (XWayland) with automatic
 English / Vietnamese localization.
 .
 Features 5 independent, freely draggable desktop widgets:
  - Large Clock with frosted-glass SF Pro Rounded numerals
  - Weather widget (OpenWeatherMap or Open-Meteo fallback)
  - System Monitor (CPU, GPU, RAM, SSD, Network)
  - Vietnamese Lunar Calendar with Can Chi
  - Rest Reminder (50-min work / 5-min break cycle)
 .
 Smart alignment guides and magnetic snapping, system tray support,
 and bilingual UI (English / Vietnamese).
EOF

cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e

case "$1" in
    purge|remove|upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
        fi
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database /usr/share/applications 2>/dev/null || true
        fi
    ;;
esac

exit 0
EOF
chmod -R 755 "${BUILD_DIR}"
chmod 644 "${BUILD_DIR}/DEBIAN/control"
chmod 755 "${BUILD_DIR}/DEBIAN/postinst" "${BUILD_DIR}/DEBIAN/postrm" "${BUILD_DIR}/usr/bin/wildos-widget"

echo "==> Building package with dpkg-deb"
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${OUTPUT_DEB}"
echo "==> Package built successfully at ${OUTPUT_DEB}"
