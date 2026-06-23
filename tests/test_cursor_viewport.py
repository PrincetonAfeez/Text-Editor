from text_editor.buffer import TextBuffer
from text_editor.cursor import Cursor, move_down, move_left, move_right, move_up
from text_editor.viewport import Viewport, ensure_visible


def test_cursor_wraps_across_line_boundaries() -> None:
    buffer = TextBuffer(["ab", "cd"])

    assert move_left(buffer, Cursor(1, 0)) == Cursor(0, 2)
    assert move_right(buffer, Cursor(0, 2)) == Cursor(1, 0)


def test_vertical_movement_uses_sticky_column() -> None:
    buffer = TextBuffer(["abcd", "x", "abcdef"])

    cursor = move_down(buffer, Cursor(0, 3), 4)
    assert cursor == Cursor(1, 1, 3)
    cursor = move_down(buffer, cursor, 4)
    assert cursor == Cursor(2, 3, 3)
    cursor = move_up(buffer, cursor, 4)
    assert cursor == Cursor(1, 1, 3)


def test_vertical_movement_tracks_visual_column_across_tabs() -> None:
    # Row 1 "\tx" has boundaries at visual columns 0, 4 (after the tab), and 5.
    buffer = TextBuffer(["ab", "\tx"])

    # From visual column 2 on "ab", moving down snaps to the nearest boundary on
    # the tab line (column 0 at visual 0, tied with column 1 at visual 4 -> 0).
    down = move_down(buffer, Cursor(0, 2), 4)
    assert down == Cursor(1, 0, 2)

    # The sticky target stays visual column 2, so moving back up lands on column 2.
    up = move_up(buffer, down, 4)
    assert up == Cursor(0, 2, 2)


def test_viewport_keeps_cursor_visible() -> None:
    viewport = ensure_visible(Viewport(0, 0), cursor_row=20, cursor_visual_col=90, content_rows=10, content_cols=40)

    assert viewport.row_offset == 11
    assert viewport.col_offset == 51

    viewport = ensure_visible(viewport, cursor_row=5, cursor_visual_col=10, content_rows=10, content_cols=40)

    assert viewport.row_offset == 5
    assert viewport.col_offset == 10
