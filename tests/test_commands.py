"""Tests for slash command system."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from commands import REGISTRY, dispatch, command


@pytest.fixture
def mock_app():
    """Mock TUI app with async action stubs."""
    app = MagicMock()
    app.action_clear = AsyncMock()
    app.action_save = AsyncMock()
    app.fs = MagicMock()
    app.fs.files = {}
    return app


class TestDispatch:
    async def test_unknown_command(self, mock_app):
        result = await dispatch(mock_app, "/foobar")
        assert "Unknown command" in result

    async def test_empty_input(self, mock_app):
        result = await dispatch(mock_app, "/")
        assert "Type /help" in result

    async def test_routes_to_help(self, mock_app):
        result = await dispatch(mock_app, "/help")
        assert "Available commands" in result

    async def test_routes_with_args(self, mock_app):
        result = await dispatch(mock_app, "/files")
        assert "empty" in result.lower()


class TestCommandDecorator:
    def test_registers_command(self):
        @command("_testcmd", help="Test command")
        async def cmd_test(app, args):
            return "ok"

        assert "_testcmd" in REGISTRY
        assert REGISTRY["_testcmd"].help == "Test command"
        del REGISTRY["_testcmd"]

    def test_registers_with_usage(self):
        @command("_testcmd2", help="Another test", usage="/testcmd2 <arg>")
        async def cmd_test2(app, args):
            return "ok"

        assert REGISTRY["_testcmd2"].usage == "/testcmd2 <arg>"
        del REGISTRY["_testcmd2"]


class TestBuiltinCommands:
    async def test_clear_calls_action(self, mock_app):
        result = await dispatch(mock_app, "/clear")
        mock_app.action_clear.assert_called_once()
        assert result is None

    async def test_sync_calls_action(self, mock_app):
        result = await dispatch(mock_app, "/sync")
        mock_app.action_save.assert_called_once()
        assert result is None

    async def test_files_empty(self, mock_app):
        result = await dispatch(mock_app, "/files")
        assert "empty" in result.lower()

    async def test_files_with_content(self, mock_app):
        mock_app.fs.files = {"/home/user/test.txt": "content"}
        result = await dispatch(mock_app, "/files")
        assert "test.txt" in result
