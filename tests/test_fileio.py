"""Tests for text_editor.fileio """

import errno
import os
import stat
import sys
from pathlib import Path

import pytest

from text_editor.buffer import TextBuffer
from text_editor.config import EditorConfig
from text_editor.errors import FileOperationError
from text_editor.fileio import read_text_file, write_text_file_atomic


def test_atomic_write_and_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    buffer = TextBuffer.from_text("one\ntwo\n")

    write_text_file_atomic(path, buffer, EditorConfig())
    loaded = read_text_file(path)

    assert loaded.lines == ["one", "two"]
    assert loaded.trailing_newline is True


def test_line_ending_policy_can_force_crlf(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    buffer = TextBuffer.from_text("one\ntwo")

    write_text_file_atomic(path, buffer, EditorConfig(line_ending_policy="crlf"))

    assert path.read_bytes() == b"one\r\ntwo\r\n"  # CRLF plus an ensured trailing newline


def test_read_missing_file_raises_user_facing_error(tmp_path: Path) -> None:
    with pytest.raises(FileOperationError):
        read_text_file(tmp_path / "missing.txt")


def test_read_directory_raises_not_a_regular_file(tmp_path: Path) -> None:
    with pytest.raises(FileOperationError, match="not a regular file"):
        read_text_file(tmp_path)


def test_open_strips_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes("﻿hello\nworld\n".encode())

    buffer = read_text_file(path)

    assert buffer.lines == ["hello", "world"]  # no stray BOM on the first line


def test_open_rejects_oversized_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import text_editor.fileio as fileio

    monkeypatch.setattr(fileio, "MAX_FILE_BYTES", 4)
    path = tmp_path / "big.txt"
    path.write_text("hello world", encoding="utf-8")

    with pytest.raises(FileOperationError, match="too large"):
        read_text_file(path)


def test_save_adds_trailing_newline_by_default(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    write_text_file_atomic(path, TextBuffer.from_text("abc"), EditorConfig())
    assert path.read_bytes() == b"abc\n"


def test_save_can_disable_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    write_text_file_atomic(path, TextBuffer.from_text("abc"), EditorConfig(ensure_trailing_newline=False))
    assert path.read_bytes() == b"abc"


def test_save_does_not_add_newline_to_empty_buffer(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    write_text_file_atomic(path, TextBuffer(), EditorConfig())
    assert path.read_bytes() == b""


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file mode semantics")
def test_save_preserves_file_permissions(tmp_path: Path) -> None:
    path = tmp_path / "script.sh"
    path.write_text("echo hi\n", encoding="utf-8")
    os.chmod(path, 0o755)

    write_text_file_atomic(path, TextBuffer.from_text("echo bye\n"), EditorConfig())

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o755


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file mode semantics")
def test_save_new_file_uses_umask_not_mkstemp_default(tmp_path: Path) -> None:
    path = tmp_path / "new.txt"
    current = os.umask(0o022)
    os.umask(current)
    expected = 0o666 & ~current

    write_text_file_atomic(path, TextBuffer.from_text("hello"), EditorConfig())

    assert stat.S_IMODE(os.stat(path).st_mode) == expected


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privilege on Windows")
def test_save_writes_through_a_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real.txt"
    target.write_text("old\n", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    write_text_file_atomic(link, TextBuffer.from_text("new\n"), EditorConfig())

    assert link.is_symlink()  # the link itself is preserved
    assert target.read_text(encoding="utf-8") == "new\n"  # the target was updated


def test_failed_save_does_not_mutate_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "test.txt"
    path.write_text("hello", encoding="utf-8")
    os.chmod(path, stat.S_IREAD)
    buffer = TextBuffer.from_text("hello")

    with pytest.raises(FileOperationError, match="read-only or permission denied"):
        write_text_file_atomic(path, buffer, EditorConfig(ensure_trailing_newline=True))

    assert buffer.trailing_newline is False


def test_read_only_save_reports_dedicated_message(tmp_path: Path) -> None:
    path = tmp_path / "locked.txt"
    path.write_text("hello", encoding="utf-8")
    os.chmod(path, stat.S_IREAD)

    with pytest.raises(FileOperationError, match="read-only or permission denied"):
        write_text_file_atomic(path, TextBuffer.from_text("hello"), EditorConfig())


def test_save_disk_full_reports_dedicated_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "out.txt"

    def raise_enospc(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("text_editor.fileio.os.replace", raise_enospc)

    with pytest.raises(FileOperationError, match="disk full"):
        write_text_file_atomic(path, TextBuffer.from_text("data"), EditorConfig())


def test_failed_save_does_not_mutate_line_ending(tmp_path: Path) -> None:
    path = tmp_path / "test.txt"
    path.write_bytes(b"a\r\nb\r\n")
    os.chmod(path, stat.S_IREAD)
    buffer = TextBuffer.from_text("a\r\nb\r\n")
    assert buffer.line_ending == "\r\n"

    with pytest.raises(FileOperationError):
        write_text_file_atomic(path, buffer, EditorConfig(line_ending_policy="lf"))

    assert buffer.line_ending == "\r\n"


def test_read_rejects_content_larger_than_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import text_editor.fileio as fileio

    monkeypatch.setattr(fileio, "MAX_FILE_BYTES", 4)
    path = tmp_path / "grow.txt"
    path.write_text("12345", encoding="utf-8")

    real_stat = Path.stat

    def stat_underreports_size(self: Path) -> os.stat_result:
        reported = real_stat(self)
        if self == path:
            return os.stat_result((2, *reported[1:]))
        return reported

    monkeypatch.setattr(Path, "stat", stat_underreports_size)

    with pytest.raises(FileOperationError, match="too large"):
        read_text_file(path)


@pytest.mark.skipif(sys.platform == "win32", reason="Unix permission semantics")
def test_read_permission_denied_reports_dedicated_message(tmp_path: Path) -> None:
    path = tmp_path / "secret.txt"
    path.write_text("hidden", encoding="utf-8")
    os.chmod(path, 0)

    with pytest.raises(FileOperationError, match="read-only or permission denied"):
        read_text_file(path)
