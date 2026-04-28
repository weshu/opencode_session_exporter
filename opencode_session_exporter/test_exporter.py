import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from exporter import (
    convert_to_markdown,
    save_markdown,
    export_single_session,
    SessionInfo,
    Message,
)


class TestConvertToMarkdown:
    def test_basic_conversion(self):
        data = {
            "id": "test-123",
            "title": "Test Session",
            "updated": "2024-01-15 10:30",
            "directory": "/test/dir",
            "messages": [
                {"role": "user", "parts": [{"type": "text", "text": "Hello"}]},
                {
                    "role": "assistant",
                    "parts": [
                        {"type": "text", "text": "Hi there!"},
                        {"type": "reasoning", "text": "Thinking..."},
                        {"type": "tool", "name": "Read"},
                    ],
                },
            ],
        }
        result = convert_to_markdown(data)

        assert "# Test Session" in result
        assert "2024-01-15 10:30" in result
        assert "/test/dir" in result
        assert "## Human" in result
        assert "Hello" in result
        assert "## AI" in result
        assert "Hi there!" in result
        assert "<details>" in result
        assert "Reasoning" in result
        assert "Tool calls: Read" in result

    def test_empty_messages(self):
        data = {
            "id": "test-456",
            "title": "Empty Session",
            "updated": "2024-01-15",
            "directory": "/test",
            "messages": [],
        }
        result = convert_to_markdown(data)

        assert "# Empty Session" in result
        assert "---" in result

    def test_title_sanitization(self):
        data = {
            "id": "test-789",
            "title": "Test: Session / WithSpecial!@#",
            "updated": "2024-01-15",
            "directory": "/test",
            "messages": [],
        }
        result = convert_to_markdown(data)

        assert "Test: Session / WithSpecial!@#" in result


class TestSaveMarkdown:
    def test_save_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "# Test"
            title = "Test Session"
            updated = "2024-01-15 10:30"
            output_dir = tmpdir

            filename = save_markdown(content, title, updated, output_dir)

            assert filename == "2024-01-15_10-30_Test-Session.md"
            filepath = os.path.join(output_dir, filename)
            assert os.path.exists(filepath)

            with open(filepath) as f:
                assert f.read() == content

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "# Test"
            title = "Test"
            updated = "2024-01-15"
            output_dir = os.path.join(tmpdir, "new", "dir")

            filename = save_markdown(content, title, updated, output_dir)

            assert os.path.exists(output_dir)


class TestExportSingleSession:
    @patch("exporter.export_session")
    def test_success(self, mock_export):
        mock_export.return_value = {
            "id": "test-123",
            "title": "Test",
            "updated": "2024-01-15",
            "directory": "/test",
            "messages": [
                {"role": "user", "parts": [{"type": "text", "text": "Hi"}]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_single_session("test-123", tmpdir)

            assert result is not None
            assert result.endswith(".md")

    @patch("exporter.export_session")
    def test_returns_none_on_failure(self, mock_export):
        mock_export.return_value = None

        result = export_single_session("invalid-id", ".")

        assert result is None


class TestSessionInfo:
    def test_dataclass(self):
        session = SessionInfo(
            id="test-123",
            title="Test Session",
            updated="2024-01-15 10:30",
            directory="/test/dir",
        )

        assert session.id == "test-123"
        assert session.title == "Test Session"
        assert session.updated == "2024-01-15 10:30"
        assert session.directory == "/test/dir"