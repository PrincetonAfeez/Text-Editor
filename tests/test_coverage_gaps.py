"""Targeted tests for remaining uncovered branches """

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from text_editor.buffer import TextBuffer
from text_editor.command_parser import CommandRequest, parse_command
from text_editor.commands import (
    execute_command_request,
    find_previous,
    goto_line,
    open_path,
    set_options,
)
from text_editor.cursor import move_right
from text_editor.errors import FileOperationError
from text_editor.fileio import read_text_file
from text_editor.render import CursesRenderer, _safe_addstr
from text_editor.state import EditorState
from tests.helpers import FakeScreen


def test_parse_set_without_assignments() -> None:
    request = parse_command(":set")
    assert request.errors == ["set requires key=value"]


def test_execute_unknown_internal_command() -> None:
    state = EditorState()
    request = CommandRequest("not_handled", args=[], errors=[])
    assert execute_command_request(state, request) is False
    assert "unknown command" in state.status_message


def test_execute_find_and_quit_commands() -> None:
    state = EditorState(buffer=TextBuffer(["needle hay"]))
    assert execute_command_request(state, parse_command(":find needle")) is True
    state2 = EditorState()
    assert execute_command_request(state2, parse_command(":quit")) is True


def test_execute_wq_save_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "note.txt"
    path.write_text("old\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("old\n"), path=path)
    from text_editor.commands import insert_printable

    insert_printable(state, "!")
    monkeypatch.setattr(
        "text_editor.commands.write_text_file_atomic",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileOperationError("fail")),
    )
    assert execute_command_request(state, parse_command(":wq")) is False


def test_goto_line_rejects_non_integer() -> None:
    state = EditorState(buffer=TextBuffer(["a"]))
    assert goto_line(state, "abc") is False
    assert "integer" in state.status_message


def test_find_previous_reports_not_found_when_matches_cleared() -> None:
    state = EditorState()
    state.search_state.query = "x"
    state.search_state.matches = []
    find_previous(state)
    assert "not found" in state.status_message


def test_set_options_refreshes_active_search() -> None:
    state = EditorState(buffer=TextBuffer(["abc"]))
    state.search_state.query = "abc"
    state.search_state.matches = []
    assert set_options(state, {"search_case_sensitive": "true"}) is True
    assert state.search_state.matches


def test_move_right_wraps_to_next_line() -> None:
    from text_editor.cursor import Cursor

    buffer = TextBuffer(["ab", "cd"])
    cursor = move_right(buffer, Cursor(0, 2))
    assert cursor.row == 1
    assert cursor.col == 0


def test_open_path_read_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe")

    state = EditorState()
    assert open_path(state, str(path)) is False
    assert "decode" in state.status_message


def test_read_stat_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "note.txt"
    path.write_text("x", encoding="utf-8")
    original = Path.stat

    def fail_stat(self: Path):  # type: ignore[no-untyped-def]
        if self == path:
            raise OSError(errno.EIO, "I/O error")
        return original(self)

    monkeypatch.setattr(Path, "stat", fail_stat)
    with pytest.raises(FileOperationError, match="could not read"):
        read_text_file(path)


def test_move_right_stays_at_end_of_file() -> None:
    from text_editor.cursor import Cursor

    buffer = TextBuffer(["last"])
    cursor = move_right(buffer, Cursor(0, 4))
    assert cursor == Cursor(0, 4)


def test_set_options_clears_search_index_when_no_matches() -> None:
    state = EditorState(buffer=TextBuffer(["zzz"]))
    state.search_state.query = "missing"
    state.search_state.current_index = 0
    assert set_options(state, {"tab_width": "8"}) is True
    assert state.search_state.current_index == -1


def test_safe_addstr_swallows_curses_errors() -> None:
    screen = FakeScreen(2, 2)

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        import curses

        raise curses.error()

    screen.addstr = boom  # type: ignore[method-assign]
    _safe_addstr(screen, 0, 0, "hello")


def test_prompt_skips_non_printable_control_keys() -> None:
    state = EditorState()
    screen = FakeScreen(8, 40, keys=["\x1a", "z", "\n"])  # Ctrl-Z is not handled in prompt
    assert CursesRenderer(screen).prompt(state, ":", initial="") == "z"
