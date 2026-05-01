import sys
import os
import tempfile
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QPalette
from PyQt6.QtCore import QTimer, Qt

# Try to import AppIndicator3 for GNOME
try:
    import gi
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3, GLib
    HAS_APP_INDICATOR = True
except (ImportError, ValueError):
    HAS_APP_INDICATOR = False


def is_gnome():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return "gnome" in desktop


class PowerMonitor:
    """Shared logic: reading watts, rendering icons."""

    def __init__(self):
        self.power_file = self.find_power_file()
        if not self.power_file:
            print("Could not find power_now in /sys/class/power_supply/")

    def find_power_file(self):
        base = "/sys/class/power_supply"
        try:
            for name in sorted(os.listdir(base)):
                candidate = os.path.join(base, name, "power_now")
                if os.path.exists(candidate):
                    return candidate
        except OSError:
            pass
        return None

    def get_watts(self):
        if not self.power_file or not os.path.exists(self.power_file):
            return None
        try:
            with open(self.power_file, 'r') as f:
                return int(f.read().strip()) / 1_000_000.0
        except Exception as e:
            print(f"Error reading power: {e}")
            return None

    def format_text(self, watts):
        if watts is None:
            return "N/A"
        return f"{int(watts)}W"
    
    def _render_pixmap(self, text):
        """Render the wattage text onto a QPixmap."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        app = QApplication.instance()
        text_color = app.palette().color(QPalette.ColorRole.WindowText)
        painter.setPen(text_color)

        font = QFont("Arial", 22, QFont.Weight.Bold)
        if len(text) > 3:
            font.setPointSize(16)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return pixmap

    def render_icon_to_file(self, text, path):
        """Render a wattage icon and save it as a PNG to a file path."""
        pixmap = self._render_pixmap(text)
        pixmap.save(path, "PNG")

    def render_icon(self, text):
        """Render a wattage icon and return a QIcon."""
        return QIcon(self._render_pixmap(text))


class GnomeTrayIcon:
    """AppIndicator3 backend for GNOME."""

    def __init__(self, monitor: PowerMonitor):
        self.monitor = monitor

        # AppIndicator3 needs a real file path for the icon
        self._tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        self._icon_path = self._tmp.name
        self._tmp.close()

        self.indicator = AppIndicator3.Indicator.new(
            "wattage-tray",
            self._icon_path,
            AppIndicator3.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Build a GTK menu (AppIndicator3 requires GTK menus, not Qt)
        from gi.repository import Gtk
        menu = Gtk.Menu()
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: QApplication.instance().quit())
        menu.append(quit_item)
        menu.show_all()
        self.indicator.set_menu(menu)

        # Use Qt timer to drive updates (GLib.timeout_add also works)
        self._qt_timer = QTimer()
        self._qt_timer.timeout.connect(self.update)
        self._qt_timer.start(1000)
        self.update()

    def update(self):
        watts = self.monitor.get_watts()
        text = self.monitor.format_text(watts)
        self.monitor.render_icon_to_file(text, self._icon_path)
        # Force AppIndicator3 to reload the icon from disk
        self.indicator.set_icon_full(self._icon_path, text)

    def show(self):
        pass  # AppIndicator3 shows automatically on .set_status(ACTIVE)

    def __del__(self):
        try:
            os.unlink(self._icon_path)
        except OSError:
            pass


class KdeTrayIcon(QSystemTrayIcon):
    """QSystemTrayIcon backend for KDE and other DEs."""

    def __init__(self, monitor: PowerMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.setToolTip("Battery Power Consumption")

        menu = QMenu()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.setContextMenu(menu)

        timer = QTimer(self)
        timer.timeout.connect(self.update_icon)
        timer.start(1000)
        self.update_icon()

    def update_icon(self):
        watts = self.monitor.get_watts()
        text = self.monitor.format_text(watts)

        if watts is not None:
            self.setToolTip(f"Power Consumption: {watts:.2f} W")
        else:
            self.setToolTip("Power Consumption: Not Available")

        self.setIcon(self.monitor.render_icon(text))


def main():
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)

    monitor = PowerMonitor()

    if is_gnome() and HAS_APP_INDICATOR:
        print("Using AppIndicator3 backend (GNOME)")
        tray = GnomeTrayIcon(monitor)
    else:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("Error: System tray is not available.")
            sys.exit(1)
        print("Using QSystemTrayIcon backend (KDE / other)")
        tray = KdeTrayIcon(monitor)
        tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()