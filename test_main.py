import os
import sys
import pytest

# Ensure PyQt runs in headless mode for tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from main import PowerMonitor
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def mock_sys_class_power(tmp_path):
    """Creates a mock /sys/class/power_supply structure."""
    base_dir = tmp_path / "sys" / "class" / "power_supply"
    base_dir.mkdir(parents=True)
    return base_dir

def test_get_watts_power_now(qapp, mock_sys_class_power):
    """Test power reading using power_now."""
    bat_dir = mock_sys_class_power / "BAT0"
    bat_dir.mkdir()
    (bat_dir / "type").write_text("Battery\n")
    (bat_dir / "power_now").write_text("15500000\n")
    
    monitor = PowerMonitor()
    monitor.base_path = str(mock_sys_class_power)
    
    watts = monitor.get_watts()
    assert watts == 15.5

def test_get_watts_current_voltage(qapp, mock_sys_class_power):
    """Test power reading using current and voltage."""
    bat_dir = mock_sys_class_power / "BAT1"
    bat_dir.mkdir()
    (bat_dir / "type").write_text("Battery\n")
    (bat_dir / "current_now").write_text("1000000\n") # 1A
    (bat_dir / "voltage_now").write_text("15000000\n") # 15V
    
    monitor = PowerMonitor()
    monitor.base_path = str(mock_sys_class_power)
    
    watts = monitor.get_watts()
    assert watts == 15.0

def test_get_watts_multiple_batteries(qapp, mock_sys_class_power):
    """Test power reading from multiple batteries."""
    bat0 = mock_sys_class_power / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery\n")
    (bat0 / "power_now").write_text("10000000\n")

    bat1 = mock_sys_class_power / "BAT1"
    bat1.mkdir()
    (bat1 / "type").write_text("Battery\n")
    (bat1 / "power_now").write_text("5500000\n")
    
    monitor = PowerMonitor()
    monitor.base_path = str(mock_sys_class_power)
    
    watts = monitor.get_watts()
    assert watts == 15.5

def test_get_watts_no_battery(qapp, mock_sys_class_power):
    """Test when no battery exists."""
    ac_dir = mock_sys_class_power / "ACAD"
    ac_dir.mkdir()
    (ac_dir / "type").write_text("Mains\n")
    (ac_dir / "power_now").write_text("15000000\n")
    
    monitor = PowerMonitor()
    monitor.base_path = str(mock_sys_class_power)
    
    watts = monitor.get_watts()
    assert watts is None

def test_get_watts_missing_base_path(qapp):
    """Test when power supply path doesn't exist."""
    monitor = PowerMonitor()
    monitor.base_path = "/non/existent/path"
    
    watts = monitor.get_watts()
    assert watts is None

def test_format_text(qapp, mocker):
    """Test the text formatting logic."""
    mocker.patch.object(PowerMonitor, "__init__", lambda self: None)
    monitor = PowerMonitor()
    
    assert monitor.format_text(15.5) == "15W"
    assert monitor.format_text(5.2) == "5.2W"
    assert monitor.format_text(10.0) == "10W"
    assert monitor.format_text(None) == "N/A"
