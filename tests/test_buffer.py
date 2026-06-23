from text_editor.buffer import TextBuffer, detect_line_ending


def test_text_roundtrip_preserves_trailing_newline_and_line_ending() -> None:
    buffer = TextBuffer.from_text("one\r\ntwo\r\n")

    assert buffer.lines == ["one", "two"]
    assert buffer.line_ending == "\r\n"
    assert buffer.trailing_newline is True
    assert buffer.to_text() == "one\r\ntwo\r\n"


def test_insert_split_join_and_delete_operations() -> None:
    buffer = TextBuffer.from_text("abc")

    assert buffer.insert_char(0, 1, "X") == (0, 2)
    assert buffer.lines == ["aXbc"]
    assert buffer.split_line(0, 2) == (1, 0)
    assert buffer.lines == ["aX", "bc"]
    assert buffer.join_with_previous(1) == (0, 2)
    assert buffer.lines == ["aXbc"]

    deleted = buffer.delete_before(0, 2)
    assert deleted == ((0, 1), "X", (0, 1))
    assert buffer.lines == ["abc"]

    deleted = buffer.delete_at(0, 1)
    assert deleted == ((0, 1), "b", (0, 1))
    assert buffer.lines == ["ac"]


def test_insert_and_delete_multiline_range() -> None:
    buffer = TextBuffer.from_text("hello")
    assert buffer.insert_string(0, 2, "X\nY") == (1, 1)
    assert buffer.lines == ["heX", "Yllo"]

    removed = buffer.delete_range((0, 2), (1, 1))
    assert removed == "X\nY"
    assert buffer.lines == ["hello"]


def test_visual_col_accounts_for_tabs() -> None:
    buffer = TextBuffer.from_text("a\tb")

    assert buffer.visual_col(0, 1, 4) == 1
    assert buffer.visual_col(0, 2, 4) == 4
    assert buffer.visual_col(0, 3, 4) == 5


def test_logical_col_for_visual_is_tab_aware() -> None:
    buffer = TextBuffer(["a\tb"])  # boundaries at visual 0, 1, 4, 5

    assert buffer.logical_col_for_visual(0, 0, 4) == 0
    assert buffer.logical_col_for_visual(0, 1, 4) == 1
    assert buffer.logical_col_for_visual(0, 4, 4) == 2
    assert buffer.logical_col_for_visual(0, 99, 4) == 3  # clamps to end of line


def test_detect_line_ending_picks_first_style() -> None:
    assert detect_line_ending("a\r\nb") == "\r\n"
    assert detect_line_ending("a\nb\r\nc") == "\n"
    assert detect_line_ending("a\rb") == "\r"
    assert detect_line_ending("no breaks") == "\n"


def test_editing_preserves_trailing_newline() -> None:
    with_newline = TextBuffer.from_text("hello\n")
    with_newline.insert_char(0, 0, "X")
    assert with_newline.to_text() == "Xhello\n"

    without_newline = TextBuffer.from_text("hello")
    without_newline.insert_char(0, 0, "X")
    assert without_newline.to_text() == "Xhello"


def test_out_of_range_row_access_clamps_instead_of_crashing() -> None:
    buffer = TextBuffer(["only"])

    assert buffer.get_line(99) == "only"
    buffer.set_line(-1, "changed")
    assert buffer.lines == ["changed"]


def test_replace_line_range_swaps_lines() -> None:
    buffer = TextBuffer(["one", "two", "three"])

    buffer.replace_line_range(1, 3, ["TWO", "THREE"])

    assert buffer.lines == ["one", "TWO", "THREE"]
