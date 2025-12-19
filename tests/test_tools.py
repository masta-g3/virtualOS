"""Tests for agent tool functions."""

from unittest.mock import patch, MagicMock
from virtual_agent import write_file, read_file, run_shell, VIRTUAL_ROOT


class TestWriteFile:
    def test_delegates_to_vfs(self, mock_ctx):
        result = write_file(mock_ctx, "test.py", "print('hi')")
        assert "Successfully wrote" in result
        assert mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/test.py"] == "print('hi')"


class TestReadFile:
    def test_delegates_to_vfs(self, mock_ctx):
        mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/test.txt"] = "content"
        result = read_file(mock_ctx, "test.txt")
        assert result == "content"


class TestRunShell:
    def test_ls_command(self, mock_ctx):
        mock_ctx.deps.fs.write("file.txt", "content")
        result = run_shell(mock_ctx, "ls")
        assert "file.txt" in result

    def test_pwd_command(self, mock_ctx):
        mock_ctx.deps.fs.cwd = "/home/user"
        result = run_shell(mock_ctx, "pwd")
        assert result == "/home/user"

    def test_cd_command(self, mock_ctx):
        run_shell(mock_ctx, "cd /tmp")
        assert mock_ctx.deps.fs.cwd == "/tmp"

    def test_rm_command(self, mock_ctx):
        mock_ctx.deps.fs.write("temp.txt", "data")
        result = run_shell(mock_ctx, "rm temp.txt")
        assert "Deleted" in result

    def test_unsupported_command(self, mock_ctx):
        result = run_shell(mock_ctx, "wget http://example.com")
        assert "not implemented" in result

    def test_python_no_workspace(self, mock_ctx):
        mock_ctx.deps.workspace_path = None
        result = run_shell(mock_ctx, "python script.py")
        assert "Error" in result
        assert "No workspace" in result

    @patch("subprocess.run")
    def test_python_executes_script(self, mock_run, mock_ctx, tmp_path):
        mock_ctx.deps.workspace_path = tmp_path
        mock_run.return_value = MagicMock(stdout="output", stderr="")

        result = run_shell(mock_ctx, "python script.py")

        mock_run.assert_called_once()
        assert "output" in result

    @patch("subprocess.run")
    def test_python_strips_virtual_root(self, mock_run, mock_ctx, tmp_path):
        mock_ctx.deps.workspace_path = tmp_path
        mock_run.return_value = MagicMock(stdout="ok", stderr="")

        run_shell(mock_ctx, f"python {VIRTUAL_ROOT}/script.py")

        call_args = mock_run.call_args
        assert call_args[0][0][1] == "script.py"
