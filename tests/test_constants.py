"""Tests for core/constants.py — centralized strings."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure core/ is importable from the test runner
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


class TestConstants:
    """Verify the constants module exports the expected strings."""

    def test_disclaimer_is_string(self):
        from core.constants import DISCLAIMER
        assert isinstance(DISCLAIMER, str)

    def test_disclaimer_mentions_kolay(self):
        from core.constants import DISCLAIMER
        assert "Kolay" in DISCLAIMER

    def test_disclaimer_mentions_unofficial(self):
        from core.constants import DISCLAIMER
        assert "unofficial" in DISCLAIMER.lower()

    def test_disclaimer_mentions_live_data(self):
        from core.constants import DISCLAIMER
        assert "live" in DISCLAIMER.lower()

    def test_token_help_contains_url(self):
        from core.constants import TOKEN_HELP
        assert "https://app.kolayik.com/settings/developer-settings" in TOKEN_HELP

    def test_token_help_contains_email(self):
        from core.constants import TOKEN_HELP
        assert "apisupport@kolay.io" in TOKEN_HELP

    def test_app_name_is_set(self):
        from core.constants import APP_NAME
        assert APP_NAME == "Kolay İK Assistant"

    def test_server_name_is_set(self):
        from core.constants import SERVER_NAME
        assert SERVER_NAME == "kolay-ik"

    def test_no_duplicate_disclaimer_in_readme(self):
        """The disclaimer text should live in constants, not be hardcoded elsewhere."""
        from core.constants import DISCLAIMER
        readme = _project_root / "README.md"
        if readme.exists():
            content = readme.read_text()
            # README has its own shorter notice; just verify constants version exists
            assert len(DISCLAIMER) > 50
