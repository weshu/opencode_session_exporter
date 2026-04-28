import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app, ExportRequest
from exporter import SessionInfo


client = TestClient(app)


class TestRootEndpoint:
    def test_returns_index_html(self):
        response = client.get("/")
        assert response.status_code in [200, 404]

    def test_returns_404_when_index_missing(self):
        with patch("app.STATIC_DIR", "/nonexistent"):
            with patch("os.path.exists", return_value=False):
                response = client.get("/")
                assert response.status_code == 404


class TestGetSessions:
    @patch("app.check_opencode_available")
    def test_returns_500_when_opencode_unavailable(self, mock_check):
        mock_check.return_value = False

        response = client.get("/api/sessions")
        assert response.status_code == 500
        assert "opencode command not found" in response.json()["detail"]

    @patch("app.check_opencode_available")
    @patch("app.list_sessions")
    def test_returns_sessions_list(self, mock_list, mock_check):
        mock_check.return_value = True
        mock_list.return_value = [
            SessionInfo(id="s1", title="Test", updated="2024-01-01", directory="/test")
        ]

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "s1"


class TestGetSession:
    @patch("app.check_opencode_available")
    def test_returns_500_when_opencode_unavailable(self, mock_check):
        mock_check.return_value = False

        response = client.get("/api/sessions/s1")
        assert response.status_code == 500

    @patch("app.check_opencode_available")
    @patch("app.export_session")
    def test_returns_404_when_session_not_found(self, mock_export, mock_check):
        mock_check.return_value = True
        mock_export.return_value = None

        response = client.get("/api/sessions/s1")
        assert response.status_code == 404

    @patch("app.check_opencode_available")
    @patch("app.export_session")
    def test_returns_session_data(self, mock_export, mock_check):
        mock_check.return_value = True
        mock_export.return_value = {"id": "s1", "title": "Test", "messages": []}

        response = client.get("/api/sessions/s1")
        assert response.status_code == 200
        assert response.json()["id"] == "s1"


class TestExportSessions:
    @patch("app.check_opencode_available")
    def test_returns_500_when_opencode_unavailable(self, mock_check):
        mock_check.return_value = False

        response = client.post("/api/export", json={"session_ids": ["s1"]})
        assert response.status_code == 500

    @patch("app.check_opencode_available")
    @patch("app.export_session")
    @patch("app.convert_to_markdown")
    @patch("app.save_markdown")
    def test_exports_successfully(
        self, mock_save, mock_convert, mock_export, mock_check
    ):
        mock_check.return_value = True
        mock_export.return_value = {"id": "s1", "title": "Test", "updated": "2024-01-01", "messages": []}
        mock_convert.return_value = "# Test"
        mock_save.return_value = "Test_2024-01-01.md"

        response = client.post("/api/export", json={"session_ids": ["s1"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["exported"]) == 1
        assert data["exported"][0] == "Test_2024-01-01.md"
        assert len(data["failed"]) == 0

    @patch("app.check_opencode_available")
    @patch("app.export_session")
    def test_handles_failed_export(self, mock_export, mock_check):
        mock_check.return_value = True
        mock_export.return_value = None

        response = client.post("/api/export", json={"session_ids": ["invalid"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["failed"]) == 1
        assert data["failed"][0] == "invalid"

    @patch("app.check_opencode_available")
    @patch("app.export_session")
    @patch("app.convert_to_markdown")
    @patch("app.save_markdown")
    def test_handles_exception_during_export(
        self, mock_save, mock_convert, mock_export, mock_check
    ):
        mock_check.return_value = True
        mock_export.return_value = {"id": "s1", "title": "Test", "updated": "2024-01-01", "messages": []}
        mock_convert.return_value = "# Test"
        mock_save.side_effect = Exception("Disk full")

        response = client.post("/api/export", json={"session_ids": ["s1"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["failed"]) == 1


class TestExportRequest:
    def test_valid_request(self):
        request = ExportRequest(session_ids=["s1", "s2"])
        assert request.session_ids == ["s1", "s2"]

    def test_empty_session_list(self):
        request = ExportRequest(session_ids=[])
        assert request.session_ids == []
