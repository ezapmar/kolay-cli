"""Tests for Behavioral Nudge Engine commands and logic."""
import time
from datetime import date
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from kolay_cli.cli import app
from kolay_cli.services import nudge
from kolay_cli import config

runner = CliRunner()

@pytest.fixture(autouse=True)
def reset_nudge_config():
    """Reset configuration before and after tests."""
    with patch("kolay_cli.config.get_config_value") as mock_get, \
         patch("kolay_cli.config.set_config_value") as mock_set:
        mock_get.return_value = {}
        yield mock_get, mock_set

def test_nudge_status_empty(reset_nudge_config, mock_client):
    """Empty queue should print a celebration."""
    # Mocking services directly
    with patch("kolay_cli.services.leave.list_leaves", return_value=[]), \
         patch("kolay_cli.services.timelog.list_timelogs", return_value={"items": [], "totalCount": 0}):
        
        result = runner.invoke(app, ["nudge", "status"])
        assert result.exit_code == 0
        assert "Zero pending" in result.output or "All clear" in result.output or "clean" in result.output or "empty" in result.output or "Queue clear" in result.output

def test_nudge_status_pending(reset_nudge_config, mock_client):
    """Pending items should print a suggestion card."""
    leaves = [{"id": "lv1", "person": {"firstName": "A"}, "status": "waiting"}]
    timelogs = {"items": [{"id": "tl1", "description": "Overtime", "person": {"firstName": "B"}, "status": "waiting"}]}
    
    with patch("kolay_cli.services.leave.list_leaves", return_value=leaves), \
         patch("kolay_cli.services.timelog.list_timelogs", return_value=timelogs):
        
        result = runner.invoke(app, ["nudge", "status"])
        assert result.exit_code == 0
        assert "AI Coach Suggestion" in result.output
        assert "Leave Request from A" in result.output

def test_nudge_configure():
    """Configuring the nudge settings iteratively."""
    with patch("kolay_cli.services.nudge.save_preferences") as mock_save:
        # Inputs: style=gamification, cadence=weekly, sprint=10
        result = runner.invoke(app, ["nudge", "configure"], input="gamification\nweekly\n10\n")
        assert result.exit_code == 0
        assert "Behavioral coaching preferences saved successfully" in result.output
        
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["style"] == "gamification"
        assert saved["cadence"] == "weekly"
        assert saved["sprint_duration"] == 10

def test_nudge_cross_service_leave(reset_nudge_config, mock_client):
    """Cross service nudge should appear at the end of leave list if timelogs pending."""
    leaves = [{"id": "lv1", "person": {"firstName": "A"}}]
    timelogs = {"items": [{"id": "tl1", "description": "Overtime", "person": {"firstName": "B"}, "status": "waiting"}]}
    
    with patch("kolay_cli.services.leave.list_leaves", return_value=leaves), \
         patch("kolay_cli.services.timelog.list_timelogs", return_value=timelogs):
        
        result = runner.invoke(app, ["leave", "list"])
        assert result.exit_code == 0
        
        # Combine lines just in case terminal formatting wrapped the text
        flat_output = result.output.replace("\n", "").replace(" ", "")
        assert "Coach'sNudge" in flat_output
        assert "TimelogfromB" in flat_output

def test_nudge_streak_logic():
    """Test updating streaks."""
    # Day 1 start
    prefs = nudge.load_preferences()
    prefs["last_all_clear_date"] = ""
    prefs["streak_count"] = 0
    with patch("kolay_cli.services.nudge.load_preferences", return_value=prefs), \
         patch("kolay_cli.services.nudge.save_preferences") as cur_save:
        streak = nudge.update_streak()
        assert streak == 1
    
    # Next day
    # We can test logic by giving it yesterday
    prefs = nudge.load_preferences()
    import datetime
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    prefs["last_all_clear_date"] = yesterday.isoformat()
    prefs["streak_count"] = 1
    
    with patch("kolay_cli.services.nudge.load_preferences", return_value=prefs), \
         patch("kolay_cli.services.nudge.save_preferences") as cur_save:
        streak = nudge.update_streak()
        assert streak == 2
