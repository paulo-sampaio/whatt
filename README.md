# Watt Widget

A KDE system tray widget built with Python and PyQt6 that shows real-time battery power consumption in Watts on the taskbar.

## Requirements

- `uv` package manager installed
- Python 3.10+
- PyQt6 (installed automatically by uv)

## How to Run

Simply use `uv run` to execute the application. This will automatically download and install the required dependencies (like PyQt6) into an isolated environment and run the app.

```bash
uv run main.py
```

## How it Works

The widget reads the system power supply file (by default `/sys/class/power_supply/BAT0/power_now`) every second. The micro-watt value is converted to Watts and drawn dynamically onto a `QPixmap`, which is then set as the application's system tray icon. The text color automatically adapts to your system theme.

To quit the widget, right-click on the tray icon and select **Quit**.
