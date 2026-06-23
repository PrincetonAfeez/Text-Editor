from text_editor.buffer import TextBuffer
from text_editor.display import (
    CONTROL_PLACEHOLDER,
    char_display_width,
    sanitize_controls,
    visible_segment,
    visual_length,
)


def test_char_display_width_handles_wide_and_narrow() -> None:
    assert char_display_width("a") == 1
    assert char_display_width(" ") == 1
    assert char_display_width("中") == 2  # CJK ideograph (East Asian Wide)
    assert char_display_width("Ａ") == 2  # fullwidth Latin A


def test_sanitize_controls_replaces_only_control_chars() -> None:
    assert sanitize_controls("plain text") == "plain text"
    assert sanitize_controls("a\x1b[31mb\x07c") == f"a{CONTROL_PLACEHOLDER}[31mb{CONTROL_PLACEHOLDER}c"
    assert sanitize_controls("nul\x00here") == f"nul{CONTROL_PLACEHOLDER}here"


def test_visible_segment_pads_and_slices_ascii() -> None:
    assert visible_segment("hello", 0, 8, 4) == "hello   "
    assert visible_segment("0123456789", 3, 4, 4) == "3456"
    assert visible_segment("", 0, 3, 4) == "   "


def test_visible_segment_expands_tabs_to_stops() -> None:
    assert visible_segment("\tab", 0, 6, 4) == "    ab"
    assert visible_segment("a\tb", 0, 6, 4) == "a   b "  # tab from col 1 -> stop at 4


def test_visible_segment_replaces_control_characters() -> None:
    out = visible_segment("a\x1bb", 0, 3, 4)
    assert out == f"a{CONTROL_PLACEHOLDER}b"


def test_visible_segment_counts_wide_characters_as_two_columns() -> None:
    # "中" is two columns wide, so it plus "x" fills three columns.
    assert visible_segment("中x", 0, 3, 4) == "中x"
    # a wide character straddling the right edge shows as a space on its visible half
    assert visible_segment("中x", 0, 1, 4) == " "
    # a wide character straddling the left edge shows a space for its visible half
    assert visible_segment("中x", 1, 2, 4) == " x"


def test_visual_col_is_wide_character_aware() -> None:
    buffer = TextBuffer(["中x"])
    assert buffer.visual_col(0, 0, 4) == 0
    assert buffer.visual_col(0, 1, 4) == 2  # after the wide char
    assert buffer.visual_col(0, 2, 4) == 3


def test_logical_col_for_visual_with_wide_characters() -> None:
    buffer = TextBuffer(["中x"])
    assert buffer.logical_col_for_visual(0, 0, 4) == 0
    assert buffer.logical_col_for_visual(0, 2, 4) == 1
    assert buffer.logical_col_for_visual(0, 3, 4) == 2


def test_visual_length_counts_wide_characters() -> None:
    assert visual_length("ab") == 2
    assert visual_length("中") == 2
    assert visual_length("a中") == 3
