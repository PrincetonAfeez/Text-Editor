"""Additional buffer primitive coverage """

from __future__ import annotations

import pytest

from text_editor.buffer import TextBuffer, detect_line_ending, normalize_newlines


def test_empty_lines_list_normalized_on_init() -> None:
    buffer = TextBuffer(lines=[])
    assert buffer.lines == [""]


def test_from_text_empty_string() -> None:
    buffer = TextBuffer.from_text("")
    assert buffer.lines == [""]
    assert buffer.trailing_newline is False


def test_insert_char_rejects_invalid_input() -> None:
    buffer = TextBuffer(["abc"])
    with pytest.raises(ValueError):
        buffer.insert_char(0, 0, "ab")
    with pytest.raises(ValueError):
        buffer.insert_char(0, 0, "\n")


def test_insert_string_empty_returns_same_position() -> None:
    buffer = TextBuffer(["abc"])
    assert buffer.insert_string(0, 1, "") == (0, 1)


def test_insert_string_multiline_splits_buffer() -> None:
    buffer = TextBuffer(["ab"])
    row, col = buffer.insert_string(0, 1, "X\nY")
    assert buffer.lines == ["aX", "Yb"]
    assert (row, col) == (1, 1)


def test_join_with_previous_at_top_returns_origin() -> None:
    buffer = TextBuffer(["only"])
    assert buffer.join_with_previous(0) == (0, 0)


def test_delete_before_at_origin_returns_none() -> None:
    buffer = TextBuffer(["a"])
    assert buffer.delete_before(0, 0) is None


def test_delete_at_end_of_file_returns_none() -> None:
    buffer = TextBuffer(["ab"])
    assert buffer.delete_at(0, 2) is None


def test_delete_at_joins_next_line() -> None:
    buffer = TextBuffer(["ab", "cd"])
    deleted = buffer.delete_at(0, 2)
    assert deleted is not None
    assert deleted[1] == "\n"
    assert buffer.lines == ["abcd"]


def test_delete_range_empty_span_returns_empty_string() -> None:
    buffer = TextBuffer(["abc"])
    assert buffer.delete_range((0, 1), (0, 1)) == ""


def test_delete_range_multiline() -> None:
    buffer = TextBuffer(["abc", "def", "ghi"])
    removed = buffer.delete_range((0, 1), (2, 1))
    assert removed == "bc\ndef\ng"
    assert buffer.lines == ["ahi"]


def test_delete_range_reversed_endpoints() -> None:
    buffer = TextBuffer(["abcdef"])
    removed = buffer.delete_range((0, 4), (0, 1))
    assert removed == "bcd"


def test_replace_line_range_empty_list_becomes_blank_line() -> None:
    buffer = TextBuffer(["a", "b", "c"])
    buffer.replace_line_range(1, 3, [])
    assert buffer.lines == ["a", ""]


def test_replace_line_range_can_clear_all_lines() -> None:
    buffer = TextBuffer(["only"])
    buffer.replace_line_range(0, 1, [])
    assert buffer.lines == [""]


def test_position_after_text_multiline() -> None:
    buffer = TextBuffer(["ab"])
    assert buffer.position_after_text((0, 1), "X\nY") == (1, 1)


def test_normalize_newlines() -> None:
    assert normalize_newlines("a\r\nb\rc") == "a\nb\nc"


def test_detect_line_ending_empty_text() -> None:
    assert detect_line_ending("") == "\n"
