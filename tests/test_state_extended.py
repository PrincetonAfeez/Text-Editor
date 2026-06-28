"""Additional editor state coverage """

from __future__ import annotations

from pathlib import Path

from text_editor.buffer import TextBuffer
from text_editor.commands import insert_printable
from text_editor.state import EditorState, Mode


def test_filename_without_path() -> None:
    assert EditorState().filename == "[No Name]"


def test_filename_with_path() -> None:
    state = EditorState(path=Path("notes.txt"))
    assert state.filename == "notes.txt"


def test_resize_clamps_and_keeps_cursor_visible() -> None:
    state = EditorState(buffer=TextBuffer(["line"] * 20))
    state.set_cursor(15, 0)
    state.resize(10, 40)
    assert state.screen_rows == 10
    assert state.cursor_row <= state.viewport_row + state.content_rows - 1


def test_apply_cursor_updates_position() -> None:
    from text_editor.cursor import Cursor

    state = EditorState(buffer=TextBuffer(["abc", "def"]))
    state.apply_cursor(Cursor(1, 2, 3))
    assert state.cursor_row == 1
    assert state.cursor_col == 2
    assert state.sticky_col == 3


def test_clear_search_resets_query() -> None:
    state = EditorState()
    state.search_state.query = "needle"
    state.clear_search()
    assert state.search_state.query == ""


def test_mark_saved_clears_dirty_and_quit_warning() -> None:
    state = EditorState()
    insert_printable(state, "x")
    state.quit_warning_armed = True
    state.mark_saved()
    assert state.dirty is False
    assert state.quit_warning_armed is False
