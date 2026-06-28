"""Tests for text_editor.cursor """

from text_editor.buffer import TextBuffer
from text_editor.cursor import Cursor, clamp, move_end, move_home, move_left, move_page_down, move_page_up, move_right


def test_move_home_and_end() -> None:
    buffer = TextBuffer(["hello"])

    assert move_home(Cursor(0, 3, 5)) == Cursor(0, 0, 5)
    assert move_end(buffer, Cursor(0, 1, 5)) == Cursor(0, 5, 5)


def test_horizontal_movement_preserves_sticky_column() -> None:
    buffer = TextBuffer(["abcd"])
    cursor = Cursor(0, 2, 7)

    assert move_left(buffer, cursor) == Cursor(0, 1, 7)
    assert move_right(buffer, move_left(buffer, cursor)) == Cursor(0, 2, 7)


def test_page_up_and_down_use_sticky_column() -> None:
    buffer = TextBuffer(["0123456789", "0123456789", "0123456789"])

    cursor = move_page_down(buffer, Cursor(0, 7), page_size=1, tab_width=4)
    assert cursor == Cursor(1, 7, 7)

    cursor = move_page_up(buffer, cursor, page_size=1, tab_width=4)
    assert cursor == Cursor(0, 7, 7)


def test_clamp_keeps_sticky_column() -> None:
    buffer = TextBuffer(["ab", "cd"])

    assert clamp(buffer, Cursor(5, 99, 3)) == Cursor(1, 2, 3)
