"""Tests for text_editor.undo """

from text_editor.buffer import TextBuffer
from text_editor.commands import (
    backspace,
    delete_forward,
    insert_newline,
    insert_printable,
    move_left,
    move_right,
    redo,
    undo,
)
from text_editor.state import EditorState
from text_editor.undo import InsertEdit, UndoHistory


def test_typed_run_groups_into_one_undo_step() -> None:
    state = EditorState()
    insert_printable(state, "a")
    insert_printable(state, "b")
    insert_printable(state, "c")

    assert state.buffer.to_text() == "abc"
    assert len(state.undo_history.undo_stack) == 1

    undo(state)
    assert state.buffer.to_text() == ""
    redo(state)
    assert state.buffer.to_text() == "abc"


def test_cursor_movement_breaks_typed_group() -> None:
    state = EditorState()
    insert_printable(state, "a")
    insert_printable(state, "b")
    move_left(state)
    move_right(state)
    insert_printable(state, "c")

    undo(state)
    assert state.buffer.to_text() == "ab"
    undo(state)
    assert state.buffer.to_text() == ""


def test_newline_split_undo_and_redo() -> None:
    state = EditorState(buffer=TextBuffer.from_text("ab"))
    state.set_cursor(0, 1)
    insert_newline(state)

    assert state.buffer.lines == ["a", "b"]
    undo(state)
    assert state.buffer.lines == ["ab"]
    redo(state)
    assert state.buffer.lines == ["a", "b"]


def test_backspace_join_undo() -> None:
    state = EditorState(buffer=TextBuffer(["a", "b"]))
    state.set_cursor(1, 0)
    backspace(state)

    assert state.buffer.lines == ["ab"]
    undo(state)
    assert state.buffer.lines == ["a", "b"]


def test_delete_forward_undo() -> None:
    state = EditorState(buffer=TextBuffer.from_text("ab"))
    delete_forward(state)

    assert state.buffer.to_text() == "b"
    undo(state)
    assert state.buffer.to_text() == "ab"


def test_undo_back_to_saved_content_clears_dirty() -> None:
    state = EditorState(buffer=TextBuffer.from_text("hello\n"))
    assert state.dirty is False

    insert_printable(state, "X")
    assert state.dirty is True

    undo(state)
    assert state.buffer.to_text() == "hello\n"
    assert state.dirty is False  # returning to saved content clears the indicator

    redo(state)
    assert state.dirty is True


def test_redo_is_invalidated_by_new_edit_after_undo() -> None:
    state = EditorState()
    insert_printable(state, "a")
    undo(state)
    insert_printable(state, "b")

    assert not state.undo_history.redo_stack
    assert state.buffer.to_text() == "b"


def test_undo_history_is_bounded_to_max_entries() -> None:
    history = UndoHistory(max_entries=3)
    for i in range(10):
        # "newline" kind never merges, so each record is a distinct entry.
        history.record(InsertEdit((0, i), "x", (0, i), (0, i + 1), kind="newline"))

    assert len(history.undo_stack) == 3
    assert history.undo_stack[-1].start == (0, 9)  # newest kept, oldest dropped
