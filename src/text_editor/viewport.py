"""Viewport math for keeping the cursor visible """

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    row_offset: int = 0
    col_offset: int = 0


def ensure_visible(
    viewport: Viewport,
    cursor_row: int,
    cursor_visual_col: int,
    content_rows: int,
    content_cols: int,
) -> Viewport:
    content_rows = max(1, content_rows)
    content_cols = max(1, content_cols)
    row_offset = max(0, viewport.row_offset)
    col_offset = max(0, viewport.col_offset)

    if cursor_row < row_offset:
        row_offset = cursor_row
    elif cursor_row >= row_offset + content_rows:
        row_offset = cursor_row - content_rows + 1

    if cursor_visual_col < col_offset:
        col_offset = cursor_visual_col
    elif cursor_visual_col >= col_offset + content_cols:
        col_offset = cursor_visual_col - content_cols + 1

    return Viewport(row_offset, col_offset)
