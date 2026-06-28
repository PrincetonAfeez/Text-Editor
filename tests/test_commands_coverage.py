"""Exhaustive command and KEY_COMMANDS coverage """

from __future__ import annotations

from pathlib import Path

import pytest

from text_editor.buffer import TextBuffer
from text_editor.command_parser import CommandRequest, parse_command
from text_editor.commands import (
    KEY_COMMANDS,
    backspace,
    delete_forward,
    execute_command_request,
    find_next,
    find_previous,
    find_query,
    insert_newline,
    insert_printable,
    insert_tab,
    move_down,
    move_end,
    move_home,
    move_left,
    move_right,
    move_up,
    open_path,
    page_down,
    page_up,
    quit_editor,
    redo,
    replace_buffer,
    save,
    save_as,
    set_options,
    show_help,
    undo,
)
from text_editor.state import EditorState


def test_key_commands_registry_matches_expected_names() -> None:
    assert set(KEY_COMMANDS) == {
        "move_left",
        "move_right",
        "move_up",
        "move_down",
        "move_home",
        "move_end",
        "page_up",
        "page_down",
        "insert_newline",
        "backspace",
        "delete_forward",
        "insert_tab",
        "undo",
        "redo",
        "quit",
        "find_next",
        "find_previous",
        "help",
    }


def test_all_key_commands_are_callable() -> None:
    state = EditorState(buffer=TextBuffer(["abc", "def"]))
    state.set_cursor(0, 1)
    for name, func in KEY_COMMANDS.items():
        func(state)
    assert state.buffer.line_count >= 1


def test_backspace_at_origin_is_noop() -> None:
    state = EditorState()
    backspace(state)
    assert state.buffer.to_text() == ""


def test_delete_forward_at_end_is_noop() -> None:
    state = EditorState(buffer=TextBuffer(["a"]))
    state.set_cursor(0, 1)
    delete_forward(state)
    assert state.buffer.to_text() == "a"


def test_insert_newline_and_tab() -> None:
    state = EditorState(buffer=TextBuffer(["ab"]))
    state.set_cursor(0, 1)
    insert_newline(state)
    assert state.buffer.lines == ["a", "b"]
    insert_tab(state)
    assert "\t" not in state.buffer.get_line(1) or state.config.expand_tabs


def test_find_next_and_previous_with_matches() -> None:
    state = EditorState(buffer=TextBuffer(["abc abc"]))
    find_query(state, "abc")
    find_next(state)
    assert "match" in state.status_message
    find_previous(state)
    assert "match" in state.status_message


def test_execute_command_request_wq_dirty_unnamed() -> None:
    state = EditorState()
    insert_printable(state, "x")
    assert execute_command_request(state, parse_command(":wq")) is False


def test_open_path_new_file(tmp_path: Path) -> None:
    state = EditorState()
    path = tmp_path / "brand_new.txt"
    assert open_path(state, str(path)) is True
    assert state.path == path


def test_save_clean_file_reports_already_saved(tmp_path: Path) -> None:
    path = tmp_path / "clean.txt"
    path.write_text("same\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("same\n"), path=path)
    assert save(state) is True
    assert state.status_message == "already saved"


def test_all_movement_commands_update_cursor() -> None:
    state = EditorState(buffer=TextBuffer(["abcdef", "xy"]))
    state.set_cursor(0, 3)

    move_up(state)
    move_down(state)
    move_left(state)
    move_right(state)
    move_home(state)
    move_end(state)
    page_up(state)
    page_down(state)

    assert 0 <= state.cursor_row < state.buffer.line_count


def test_insert_printable_empty_string_is_noop() -> None:
    state = EditorState()
    insert_printable(state, "")
    assert state.buffer.to_text() == ""


def test_undo_and_redo_empty_stack_messages() -> None:
    state = EditorState()
    undo(state)
    assert state.status_message == "nothing to undo"
    redo(state)
    assert state.status_message == "nothing to redo"


def test_save_without_path_reports_error() -> None:
    state = EditorState()
    assert save(state) is False
    assert "saveas" in state.status_message


def test_save_reports_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "note.txt"
    path.write_text("old", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("old"), path=path)
    insert_printable(state, "!")

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        from text_editor.errors import FileOperationError

        raise FileOperationError("boom")

    monkeypatch.setattr("text_editor.commands.write_text_file_atomic", boom)
    assert save(state) is False
    assert state.status_message == "boom"


def test_save_as_reports_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = EditorState(buffer=TextBuffer.from_text("data"))

    def boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        from text_editor.errors import FileOperationError

        raise FileOperationError("boom")

    monkeypatch.setattr("text_editor.commands.write_text_file_atomic", boom)
    assert save_as(state, str(tmp_path / "out.txt")) is False


def test_quit_editor_force_and_double_confirm() -> None:
    state = EditorState(buffer=TextBuffer.from_text("dirty"))
    insert_printable(state, "!")
    quit_editor(state)
    assert state.quit_warning_armed
    assert not state.should_quit
    quit_editor(state)
    assert state.should_quit

    state2 = EditorState()
    quit_editor(state2, force=True)
    assert state2.should_quit


def test_open_path_refuses_dirty_buffer(tmp_path: Path) -> None:
    other = tmp_path / "other.txt"
    other.write_text("x\n", encoding="utf-8")
    state = EditorState()
    insert_printable(state, "z")
    assert open_path(state, str(other)) is False


def test_find_query_with_no_matches() -> None:
    state = EditorState(buffer=TextBuffer(["abc"]))
    assert find_query(state, "zzz") is False
    assert "not found" in state.status_message


def test_find_next_and_previous_without_active_search() -> None:
    state = EditorState()
    find_next(state)
    assert state.status_message == "no active search"
    find_previous(state)
    assert state.status_message == "no active search"


def test_find_next_with_no_matches_in_state() -> None:
    state = EditorState()
    state.search_state.query = "x"
    state.search_state.matches = []
    find_next(state)
    assert "not found" in state.status_message


def test_goto_line_invalid_and_valid() -> None:
    state = EditorState(buffer=TextBuffer(["a", "b", "c"]))
    assert execute_command_request(state, parse_command(":goto abc")) is False
    assert execute_command_request(state, parse_command(":goto 2")) is True
    assert state.cursor_row == 1


def test_set_options_rejects_invalid_value() -> None:
    state = EditorState()
    assert set_options(state, {"tab_width": "nope"}) is False
    assert "integer" in state.status_message


def test_execute_command_request_empty_and_unknown() -> None:
    state = EditorState()
    assert execute_command_request(state, CommandRequest(None, errors=["empty command"])) is False
    assert execute_command_request(state, parse_command(":nope")) is False
    assert execute_command_request(state, CommandRequest(None, errors=[])) is False


def test_execute_command_request_help_quit_and_navigation_commands() -> None:
    state = EditorState()
    assert execute_command_request(state, parse_command(":help")) is True
    assert execute_command_request(state, parse_command(":next")) is True
    assert execute_command_request(state, parse_command(":prev")) is True
    assert execute_command_request(state, parse_command(":quit!")) is True
    assert state.should_quit


def test_execute_command_request_wq_clean_unnamed() -> None:
    state = EditorState()
    assert execute_command_request(state, parse_command(":wq")) is True
    assert state.should_quit


def test_execute_command_request_write_and_open(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("start\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("start\n"), path=path)
    insert_printable(state, "!")
    assert execute_command_request(state, parse_command(":write")) is True

    state2 = EditorState()
    other = tmp_path / "other.txt"
    other.write_text("other\n", encoding="utf-8")
    assert execute_command_request(state2, parse_command(f':open "{other}"')) is True


def test_replace_buffer_resets_editor_state(tmp_path: Path) -> None:
    state = EditorState(buffer=TextBuffer.from_text("old"))
    insert_printable(state, "!")
    replace_buffer(state, TextBuffer.from_text("new\n"), tmp_path / "new.txt")
    assert state.buffer.to_text() == "new\n"
    assert state.dirty is False
    assert not state.undo_history.undo_stack


def test_show_help_sets_status() -> None:
    state = EditorState()
    show_help(state)
    assert "^S save" in state.status_message


def test_help_key_command() -> None:
    state = EditorState()
    KEY_COMMANDS["help"](state)
    assert "^P command" in state.status_message
