"""Undo/redo history implemented with reversible edit commands """

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .buffer import Position, TextBuffer


class EditableState(Protocol):
    buffer: TextBuffer

    def set_cursor(self, row: int, col: int, sticky_col: int | None = None) -> None: ...

    def recompute_dirty(self) -> None: ...


@dataclass
class InsertEdit:
    start: Position
    text: str
    before_cursor: Position
    after_cursor: Position
    kind: str = "insert"

    def undo(self, state: EditableState) -> None:
        end = state.buffer.position_after_text(self.start, self.text)
        state.buffer.delete_range(self.start, end)
        state.set_cursor(*self.before_cursor)
        state.recompute_dirty()

    def redo(self, state: EditableState) -> None:
        state.buffer.insert_string(*self.start, self.text)
        state.set_cursor(*self.after_cursor)
        state.recompute_dirty()

    def can_merge(self, other: object) -> bool:
        return (
            isinstance(other, InsertEdit)
            and self.kind == "typing"
            and other.kind == "typing"
            and "\n" not in self.text
            and "\n" not in other.text
            and self.after_cursor == other.start
        )

    def merge(self, other: InsertEdit) -> None:
        self.text += other.text
        self.after_cursor = other.after_cursor


@dataclass
class DeleteEdit:
    start: Position
    text: str
    before_cursor: Position
    after_cursor: Position

    def undo(self, state: EditableState) -> None:
        state.buffer.insert_string(*self.start, self.text)
        state.set_cursor(*self.before_cursor)
        state.recompute_dirty()

    def redo(self, state: EditableState) -> None:
        end = state.buffer.position_after_text(self.start, self.text)
        state.buffer.delete_range(self.start, end)
        state.set_cursor(*self.after_cursor)
        state.recompute_dirty()

    def can_merge(self, other: object) -> bool:
        return False


UndoableEdit = InsertEdit | DeleteEdit


@dataclass
class UndoHistory:
    undo_stack: list[UndoableEdit] = field(default_factory=list)
    redo_stack: list[UndoableEdit] = field(default_factory=list)
    max_entries: int = 1000
    _merge_blocked: bool = False

    def record(self, edit: UndoableEdit) -> None:
        if self.undo_stack and not self._merge_blocked and self.undo_stack[-1].can_merge(edit):
            last = self.undo_stack[-1]
            if isinstance(last, InsertEdit) and isinstance(edit, InsertEdit):
                last.merge(edit)
        else:
            self.undo_stack.append(edit)
            # Bound memory on long sessions by dropping the oldest edits.
            if len(self.undo_stack) > self.max_entries:
                del self.undo_stack[: len(self.undo_stack) - self.max_entries]
        self.redo_stack.clear()
        self._merge_blocked = False

    def break_group(self) -> None:
        self._merge_blocked = True

    def undo(self, state: EditableState) -> bool:
        if not self.undo_stack:
            return False
        edit = self.undo_stack.pop()
        edit.undo(state)
        self.redo_stack.append(edit)
        self._merge_blocked = True
        return True

    def redo(self, state: EditableState) -> bool:
        if not self.redo_stack:
            return False
        edit = self.redo_stack.pop()
        edit.redo(state)
        self.undo_stack.append(edit)
        self._merge_blocked = True
        return True

    def clear(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._merge_blocked = False
