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

def test_find_power_file_success(qapp, mock_sys_class_power, mocker):
    """Test that find_power_file correctly locates the power_now file."""
    # Create a dummy battery directory
    bat_dir = mock_sys_class_power / "BAT0"
    bat_dir.mkdir()
    power_file = bat_dir / "power_now"
    power_file.write_text("15000000")
    
    # Mock os.listdir to use our tmp_path
    mocker.patch("os.listdir", return_value=["BAT0"])
    
    # Mock os.path.join and os.path.exists to point to our temp dir
    def mock_join(base, name, filename):
        if base == "/sys/class/power_supply":
            return str(mock_sys_class_power / name / filename)
        return os.path.join(base, name, filename)
        
    mocker.patch("os.path.join", side_effect=mock_join)
    
    # Original exists function
    orig_exists = os.path.exists
    def mock_exists(path):
        if str(mock_sys_class_power) in path:
            return orig_exists(path)
        return orig_exists(path)
        
    mocker.patch("os.path.exists", side_effect=mock_exists)

    monitor = PowerMonitor()
    assert monitor.find_power_file() == str(power_file)

def test_find_power_file_not_found(qapp, mock_sys_class_power, mocker):
    """Test find_power_file when no battery exists."""
    mocker.patch("os.listdir", return_value=["ACAD"])
    
    def mock_join(base, name, filename):
        if base == "/sys/class/power_supply":
            return str(mock_sys_class_power / name / filename)
        return os.path.join(base, name, filename)
        
    mocker.patch("os.path.join", side_effect=mock_join)

    monitor = PowerMonitor()
    assert monitor.find_power_file() is None

def test_get_watts(qapp, tmp_path, mocker):
    """Test power reading."""
    bat_dir = tmp_path / "BAT0"
    bat_dir.mkdir()
    
    power_file = bat_dir / "power_now"
    power_file.write_text("15500000\n")
    
    # Patch PowerMonitor.__init__ to avoid finding file during init
    mocker.patch.object(PowerMonitor, "__init__", lambda self: None)
    
    monitor = PowerMonitor()
    monitor.power_file = str(power_file)
    
    watts = monitor.get_watts()
    assert watts == 15.5

def test_get_watts_missing_file(qapp, mocker):
    """Test when power file doesn't exist."""
    mocker.patch.object(PowerMonitor, "__init__", lambda self: None)
    monitor = PowerMonitor()
    monitor.power_file = "/non/existent/path/power_now"
    
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
