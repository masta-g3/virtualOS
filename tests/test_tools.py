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

    def test_mkdir_creates_directory_marker(self, mock_ctx):
        result = run_shell(mock_ctx, "mkdir subdir")
        assert "Created directory" in result
        assert f"{VIRTUAL_ROOT}/subdir/.dir" in mock_ctx.deps.fs.files

    def test_mkdir_no_arg_error(self, mock_ctx):
        result = run_shell(mock_ctx, "mkdir")
        assert "Error" in result

    def test_touch_creates_empty_file(self, mock_ctx):
        result = run_shell(mock_ctx, "touch newfile.txt")
        assert "Touched" in result
        assert mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/newfile.txt"] == ""

    def test_touch_existing_file_unchanged(self, mock_ctx):
        mock_ctx.deps.fs.write("existing.txt", "content")
        run_shell(mock_ctx, "touch existing.txt")
        assert mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/existing.txt"] == "content"

    def test_touch_no_arg_error(self, mock_ctx):
        result = run_shell(mock_ctx, "touch")
        assert "Error" in result

    def test_mv_moves_file(self, mock_ctx):
        mock_ctx.deps.fs.write("old.txt", "data")
        result = run_shell(mock_ctx, "mv old.txt new.txt")
        assert "Moved" in result
        assert f"{VIRTUAL_ROOT}/old.txt" not in mock_ctx.deps.fs.files
        assert mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/new.txt"] == "data"

    def test_mv_missing_source_error(self, mock_ctx):
        result = run_shell(mock_ctx, "mv nonexistent.txt dest.txt")
        assert "Error" in result
        assert "does not exist" in result

    def test_mv_wrong_args_error(self, mock_ctx):
        result = run_shell(mock_ctx, "mv onlyonepath")
        assert "Error" in result

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


class TestGrepCommand:
    """Tests for grep command in run_shell."""

    def test_grep_finds_matches(self, mock_ctx):
        """Grep returns matching lines with file:line:content format."""
        mock_ctx.deps.fs.write("test.py", "def foo():\n    return 42\ndef bar():\n    pass")
        result = run_shell(mock_ctx, "grep def")
        assert "test.py:1:def foo():" in result
        assert "test.py:3:def bar():" in result

    def test_grep_no_matches(self, mock_ctx):
        """Grep returns message when no matches found."""
        mock_ctx.deps.fs.write("test.txt", "hello world")
        result = run_shell(mock_ctx, "grep xyz")
        assert result == "No matches found."

    def test_grep_specific_file(self, mock_ctx):
        """Grep can search a specific file."""
        mock_ctx.deps.fs.write("a.txt", "match")
        mock_ctx.deps.fs.write("b.txt", "match")
        result = run_shell(mock_ctx, "grep match a.txt")
        assert "a.txt" in result
        assert "b.txt" not in result

    def test_grep_regex(self, mock_ctx):
        """Grep supports regex patterns."""
        mock_ctx.deps.fs.write("test.txt", "foo123\nbar456\nbaz")
        result = run_shell(mock_ctx, r"grep \d+")
        assert "test.txt:1:foo123" in result
        assert "test.txt:2:bar456" in result
        assert "baz" not in result

    def test_grep_context_after(self, mock_ctx):
        """Grep -A shows lines after match."""
        mock_ctx.deps.fs.write("test.txt", "a\nmatch\nb\nc")
        result = run_shell(mock_ctx, "grep -A 2 match")
        assert "test.txt:2:match" in result
        assert "test.txt:3-b" in result
        assert "test.txt:4-c" in result

    def test_grep_context_before(self, mock_ctx):
        """Grep -B shows lines before match."""
        mock_ctx.deps.fs.write("test.txt", "a\nb\nmatch\nc")
        result = run_shell(mock_ctx, "grep -B 2 match")
        assert "test.txt:1-a" in result
        assert "test.txt:2-b" in result
        assert "test.txt:3:match" in result

    def test_grep_context_separator(self, mock_ctx):
        """Grep separates non-adjacent match groups with --."""
        mock_ctx.deps.fs.write("test.txt", "match1\na\nb\nc\nmatch2")
        result = run_shell(mock_ctx, "grep match")
        assert "--" in result

    def test_grep_truncates_large_output(self, mock_ctx):
        """Grep truncates output at 100 lines."""
        content = "\n".join([f"match line {i}" for i in range(150)])
        mock_ctx.deps.fs.write("big.txt", content)
        result = run_shell(mock_ctx, "grep match")
        assert "showing first 100" in result

    def test_grep_invalid_regex(self, mock_ctx):
        """Grep returns error for invalid regex."""
        mock_ctx.deps.fs.write("test.txt", "content")
        result = run_shell(mock_ctx, "grep [invalid")
        assert "Error" in result
        assert "Invalid regex" in result

    def test_grep_usage_no_pattern(self, mock_ctx):
        """Grep shows usage when no pattern provided."""
        result = run_shell(mock_ctx, "grep")
        assert "Usage" in result

    def test_grep_skips_dir_markers(self, mock_ctx):
        """Grep skips .dir directory markers."""
        mock_ctx.deps.fs.files[f"{VIRTUAL_ROOT}/subdir/.dir"] = ""
        mock_ctx.deps.fs.write("test.txt", "content")
        result = run_shell(mock_ctx, "grep content")
        assert ".dir" not in result
