"""Tests for the KolayClient API wrapper."""
import pytest
from unittest.mock import MagicMock, patch
import requests

from kolay_cli.api import KolayClient, APIError, safe_id


class TestSafeId:
    def test_valid_id(self):
        assert safe_id("abc123-XYZ_test") == "abc123-XYZ_test"

    def test_strips_whitespace(self):
        assert safe_id(" abc123  ") == "abc123"

    def test_empty_raises(self):
        with pytest.raises(APIError, match="cannot be empty"):
            safe_id("")

    def test_whitespace_only_raises(self):
        with pytest.raises(APIError, match="cannot be empty"):
            safe_id(" ")

    def test_path_traversal_raises(self):
        with pytest.raises(APIError, match="illegal characters"):
            safe_id("../../etc/passwd")

    def test_slash_raises(self):
        with pytest.raises(APIError, match="illegal characters"):
            safe_id("abc/def")


class TestKolayClientInit:
    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("KOLAY_API_TOKEN", raising=False)
        monkeypatch.setenv("KOLAY_BASE_URL", "https://api.kolayik.com")
        with patch("kolay_cli.api.client.config.get_api_token", return_value=None), \
             patch("kolay_cli.api.client.config.get_base_url", return_value="https://api.kolayik.com"):
            with pytest.raises(APIError, match="No API token found"):
                KolayClient(token=None)

    def test_http_base_url_raises(self):
        with pytest.raises(APIError, match="HTTPS"):
            KolayClient(token="tok", base_url="http://api.kolayik.com")

    def test_https_base_url_ok(self):
        client = KolayClient(token="tok", base_url="https://api.kolayik.com")
        assert client.base_url == "https://api.kolayik.com"

    def test_trailing_slash_stripped(self):
        client = KolayClient(token="tok", base_url="https://api.kolayik.com/")
        assert client.base_url == "https://api.kolayik.com"


class TestKolayClientRequest:
    def _make_client(self):
        return KolayClient(token="tok", base_url="https://api.kolayik.com")

    def test_get_success(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.content = b'{"data": "ok"}'
        mock_resp.json.return_value = {"data": "ok"}
        mock_resp.raise_for_status = MagicMock()
        client.session.request = MagicMock(return_value=mock_resp)

        result = client.get("v2/profile/me")
        assert result == {"data": "ok"}
        call_args = client.session.request.call_args
        assert call_args[0] == ("GET", "https://api.kolayik.com/v2/profile/me")
        assert call_args[1]["timeout"] == 30

    def test_post_sends_json(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.content = b'{"data": "created"}'
        mock_resp.json.return_value = {"data": "created"}
        mock_resp.raise_for_status = MagicMock()
        client.session.request = MagicMock(return_value=mock_resp)

        result = client.post("v2/person/create", data={"name": "Test"})
        assert result == {"data": "created"}
        call_args = client.session.request.call_args
        assert call_args[0] == ("POST", "https://api.kolayik.com/v2/person/create")

    def test_404_raises_api_error(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {}
        http_error = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_error)
        client.session.request = MagicMock(return_value=mock_resp)
        with pytest.raises(APIError):
            client.get("v2/person/view/nonexistent")

    def test_401_raises_api_error_with_hint(self):
        """401 should raise APIError with a recovery hint."""
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {}
        http_error = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_error)
        client.session.request = MagicMock(return_value=mock_resp)
        with pytest.raises(APIError) as exc_info:
            client.get("v2/profile/me")
        err = exc_info.value
        assert err.status_code == 401
        assert err.hint is not None
        assert "login" in err.hint.lower()

    def test_429_raises_api_error(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {}
        http_error = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_error)
        client.session.request = MagicMock(return_value=mock_resp)
        with pytest.raises(APIError) as exc_info:
            client.get("v2/person/list")
        assert exc_info.value.status_code == 429

    def test_500_raises_api_error(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {}
        http_error = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_error)
        client.session.request = MagicMock(return_value=mock_resp)
        with pytest.raises(APIError) as exc_info:
            client.get("v2/person/list")
        assert exc_info.value.status_code == 500

    def test_connection_error_raises(self):
        client = self._make_client()
        client.session.request = MagicMock(side_effect=requests.exceptions.ConnectionError)
        with pytest.raises(APIError, match="connect"):
            client.get("v2/profile/me")

    def test_timeout_raises(self):
        client = self._make_client()
        client.session.request = MagicMock(side_effect=requests.exceptions.Timeout)
        with pytest.raises(APIError, match="timed out"):
            client.get("v2/profile/me")

    def test_path_traversal_blocked(self):
        client = self._make_client()
        with pytest.raises(APIError, match="Invalid API endpoint"):
            client.get("../../etc/passwd")

    def test_absolute_url_blocked(self):
        client = self._make_client()
        with pytest.raises(APIError, match="Invalid API endpoint"):
            client.get("/v2/profile/me")

    def test_empty_response_returns_dict(self):
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.content = b""
        mock_resp.raise_for_status = MagicMock()
        client.session.request = MagicMock(return_value=mock_resp)
        result = client.delete("v2/timelog/delete/abc123")
        assert result == {}
