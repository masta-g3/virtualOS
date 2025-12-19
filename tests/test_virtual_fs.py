"""Tests for VirtualFileSystem."""

from virtual_agent import VIRTUAL_ROOT


class TestPathResolution:
    def test_absolute_path(self, vfs):
        assert vfs._resolve("/foo/bar") == "/foo/bar"

    def test_relative_path(self, vfs):
        vfs.cwd = "/home/user"
        assert vfs._resolve("docs/readme.md") == "/home/user/docs/readme.md"

    def test_parent_directory(self, vfs):
        vfs.cwd = "/home/user/docs"
        assert vfs._resolve("../readme.md") == "/home/user/readme.md"

    def test_current_directory_dot(self, vfs):
        vfs.cwd = "/home/user"
        assert vfs._resolve("./file.txt") == "/home/user/file.txt"

    def test_multiple_parent_refs(self, vfs):
        vfs.cwd = "/home/user/a/b/c"
        assert vfs._resolve("../../file.txt") == "/home/user/a/file.txt"


class TestFileOperations:
    def test_write_creates_file(self, vfs):
        result = vfs.write("test.txt", "hello")
        assert "Successfully wrote" in result
        assert vfs.files[f"{VIRTUAL_ROOT}/test.txt"] == "hello"

    def test_write_overwrites_file(self, vfs):
        vfs.write("test.txt", "first")
        vfs.write("test.txt", "second")
        assert vfs.files[f"{VIRTUAL_ROOT}/test.txt"] == "second"

    def test_read_existing_file(self, vfs):
        vfs.files[f"{VIRTUAL_ROOT}/test.txt"] = "content"
        assert vfs.read("test.txt") == "content"

    def test_read_missing_file(self, vfs):
        result = vfs.read("nonexistent.txt")
        assert "Error" in result
        assert "does not exist" in result

    def test_delete_existing_file(self, vfs):
        vfs.files[f"{VIRTUAL_ROOT}/temp.txt"] = "data"
        result = vfs.delete("temp.txt")
        assert "Deleted" in result
        assert f"{VIRTUAL_ROOT}/temp.txt" not in vfs.files

    def test_delete_missing_file(self, vfs):
        result = vfs.delete("nonexistent.txt")
        assert "Error" in result


class TestListDir:
    def test_empty_directory(self, vfs):
        result = vfs.list_dir("/empty")
        assert result == "(empty directory)"

    def test_lists_files(self, vfs):
        vfs.files[f"{VIRTUAL_ROOT}/a.txt"] = "a"
        vfs.files[f"{VIRTUAL_ROOT}/b.txt"] = "b"
        listing = vfs.list_dir(VIRTUAL_ROOT)
        assert "a.txt" in listing
        assert "b.txt" in listing

    def test_excludes_nested_files(self, vfs):
        vfs.files[f"{VIRTUAL_ROOT}/top.txt"] = "top"
        vfs.files[f"{VIRTUAL_ROOT}/sub/nested.txt"] = "nested"
        listing = vfs.list_dir(VIRTUAL_ROOT)
        assert "top.txt" in listing
        assert "nested.txt" not in listing


class TestDiskSync:
    def test_load_from_disk(self, vfs, tmp_path):
        (tmp_path / "file.txt").write_text("loaded")
        count = vfs.load_from_disk(tmp_path, "/virtual")
        assert count == 1
        assert vfs.files["/virtual/file.txt"] == "loaded"

    def test_save_to_disk(self, vfs, tmp_path):
        vfs.files["/virtual/output.txt"] = "saved"
        count = vfs.save_to_disk(tmp_path, "/virtual")
        assert count == 1
        assert (tmp_path / "output.txt").read_text() == "saved"

    def test_load_nonexistent_path(self, vfs, tmp_path):
        count = vfs.load_from_disk(tmp_path / "nonexistent")
        assert count == 0
