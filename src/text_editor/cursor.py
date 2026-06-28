"""Pure cursor movement rules """

from __future__ import annotations

from dataclasses import dataclass

from .buffer import TextBuffer


@dataclass(frozen=True)
class Cursor:
    row: int = 0
    col: int = 0
    sticky_col: int | None = None


def clamp(buffer: TextBuffer, cursor: Cursor) -> Cursor:
    row, col = buffer.clamp_position(cursor.row, cursor.col)
    return Cursor(row, col, cursor.sticky_col)


def move_left(buffer: TextBuffer, cursor: Cursor) -> Cursor:
    sticky = cursor.sticky_col
    if cursor.col > 0:
        return Cursor(cursor.row, cursor.col - 1, sticky)
    if cursor.row > 0:
        previous_row = cursor.row - 1
        return Cursor(previous_row, len(buffer.get_line(previous_row)), sticky)
    return Cursor(0, 0, sticky)


def move_right(buffer: TextBuffer, cursor: Cursor) -> Cursor:
    sticky = cursor.sticky_col
    line_len = len(buffer.get_line(cursor.row))
    if cursor.col < line_len:
        return Cursor(cursor.row, cursor.col + 1, sticky)
    if cursor.row < buffer.line_count - 1:
        return Cursor(cursor.row + 1, 0, sticky)
    return Cursor(cursor.row, cursor.col, sticky)


def _sticky_target(buffer: TextBuffer, cursor: Cursor, tab_width: int) -> int:
    """The visual column vertical movement should aim for."""

    if cursor.sticky_col is not None:
        return cursor.sticky_col
    return buffer.visual_col(cursor.row, cursor.col, tab_width)


def _to_row(buffer: TextBuffer, row: int, target_visual: int, tab_width: int) -> Cursor:
    col = buffer.logical_col_for_visual(row, target_visual, tab_width)
    return Cursor(row, col, target_visual)


def move_up(buffer: TextBuffer, cursor: Cursor, tab_width: int) -> Cursor:
    target = _sticky_target(buffer, cursor, tab_width)
    row = max(0, cursor.row - 1)
    return _to_row(buffer, row, target, tab_width)


def move_down(buffer: TextBuffer, cursor: Cursor, tab_width: int) -> Cursor:
    target = _sticky_target(buffer, cursor, tab_width)
    row = min(buffer.line_count - 1, cursor.row + 1)
    return _to_row(buffer, row, target, tab_width)


def move_home(cursor: Cursor) -> Cursor:
    return Cursor(cursor.row, 0, cursor.sticky_col)


def move_end(buffer: TextBuffer, cursor: Cursor) -> Cursor:
    return Cursor(cursor.row, len(buffer.get_line(cursor.row)), cursor.sticky_col)


def move_page_up(buffer: TextBuffer, cursor: Cursor, page_size: int, tab_width: int) -> Cursor:
    target = _sticky_target(buffer, cursor, tab_width)
    row = max(0, cursor.row - max(1, page_size))
    return _to_row(buffer, row, target, tab_width)


def move_page_down(buffer: TextBuffer, cursor: Cursor, page_size: int, tab_width: int) -> Cursor:
    target = _sticky_target(buffer, cursor, tab_width)
    row = min(buffer.line_count - 1, cursor.row + max(1, page_size))
    return _to_row(buffer, row, target, tab_width)
