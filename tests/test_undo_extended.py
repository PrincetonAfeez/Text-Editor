"""Additional undo stack coverage """

from __future__ import annotations

from text_editor.buffer import TextBuffer
from text_editor.state import EditorState
from text_editor.undo import DeleteEdit, InsertEdit, UndoHistory


def test_insert_edit_direct_undo_redo() -> None:
    state = EditorState(buffer=TextBuffer(["hello"]))
    edit = InsertEdit((0, 5), "!", (0, 5), (0, 6), kind="insert")
    edit.undo(state)
    assert state.buffer.get_line(0) == "hello"
    edit.redo(state)
    assert state.buffer.get_line(0) == "hello!"


def test_delete_edit_direct_undo_redo() -> None:
    state = EditorState(buffer=TextBuffer(["hello"]))
    edit = DeleteEdit((0, 4), "o", (0, 5), (0, 4))
    edit.redo(state)
    assert state.buffer.get_line(0) == "hell"
    edit.undo(state)
    assert state.buffer.get_line(0) == "hello"


def test_insert_edit_can_merge_requires_typing_kind() -> None:
    first = InsertEdit((0, 0), "a", (0, 0), (0, 1), kind="typing")
    second = InsertEdit((0, 1), "b", (0, 1), (0, 2), kind="newline")
    assert first.can_merge(second) is False


def test_delete_edit_never_merges() -> None:
    edit = DeleteEdit((0, 0), "a", (0, 1), (0, 0))
    assert edit.can_merge(edit) is False


def test_undo_history_clear_resets_stacks() -> None:
    history = UndoHistory()
    history.record(InsertEdit((0, 0), "a", (0, 0), (0, 1)))
    history.undo(state := EditorState())
    history.clear()
    assert history.undo_stack == []
    assert history.redo_stack == []


def test_undo_and_redo_return_false_when_empty() -> None:
    state = EditorState()
    history = UndoHistory()
    assert history.undo(state) is False
    assert history.redo(state) is False
