"""Additional fileio helper coverage """

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from text_editor.buffer import TextBuffer
from text_editor.config import EditorConfig
from text_editor.errors import FileOperationError
from text_editor.fileio import effective_line_ending, read_text_file, text_for_save, write_text_file_atomic


def test_effective_line_ending_respects_policy() -> None:
    buffer = TextBuffer.from_text("a\r\nb\r\n")
    assert effective_line_ending(buffer, EditorConfig(line_ending_policy="preserve")) == "\r\n"
    assert effective_line_ending(buffer, EditorConfig(line_ending_policy="lf")) == "\n"
    assert effective_line_ending(buffer, EditorConfig(line_ending_policy="crlf")) == "\r\n"


def test_text_for_save_reports_metadata_without_mutation() -> None:
    buffer = TextBuffer.from_text("a\nb")
    text, ending, changed, added = text_for_save(buffer, EditorConfig(line_ending_policy="crlf"))
    assert text.endswith("\r\n")
    assert changed is True
    assert added is True
    assert buffer.line_ending == "\n"


def test_text_for_save_empty_buffer() -> None:
    text, ending, changed, added = text_for_save(TextBuffer(), EditorConfig())
    assert text == ""
    assert added is False


def test_read_file_not_found_message(tmp_path: Path) -> None:
    with pytest.raises(FileOperationError, match="file not found"):
        read_text_file(tmp_path / "missing.txt")


def test_read_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "binary.txt"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(FileOperationError, match="could not decode"):
        read_text_file(path)


def test_read_generic_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "broken.txt"
    path.write_text("hello", encoding="utf-8")
    original = Path.read_text

    def patched_read_text(self: Path, encoding: str = "utf-8") -> str:
        if self == path:
            raise OSError(errno.EIO, "I/O error")
        return original(self, encoding)

    monkeypatch.setattr(Path, "read_text", patched_read_text)
    with pytest.raises(FileOperationError, match="could not read"):
        read_text_file(path)


def test_save_to_missing_directory(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "file.txt"
    with pytest.raises(FileOperationError, match="directory does not exist"):
        write_text_file_atomic(path, TextBuffer.from_text("x"), EditorConfig())


def test_fsync_directory_swallows_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import text_editor.fileio as fileio

    monkeypatch.setattr(fileio.os, "O_DIRECTORY", 0o200000, raising=False)

    def fail_open(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("nope")

    monkeypatch.setattr(fileio.os, "open", fail_open)
    fileio._fsync_directory(tmp_path)  # should not raise


def test_fsync_directory_closes_on_fsync_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import text_editor.fileio as fileio

    monkeypatch.setattr(fileio.os, "O_DIRECTORY", 0o200000, raising=False)
    closed: list[int] = []

    def fake_open(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return 7

    def fail_fsync(_fd: int) -> None:
        raise OSError("fsync failed")

    def fake_close(fd: int) -> None:
        closed.append(fd)

    monkeypatch.setattr(fileio.os, "open", fake_open)
    monkeypatch.setattr(fileio.os, "fsync", fail_fsync)
    monkeypatch.setattr(fileio.os, "close", fake_close)
    fileio._fsync_directory(tmp_path)
    assert closed == [7]
