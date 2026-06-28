"""Additional display helper coverage """

from __future__ import annotations

from text_editor.display import is_control, visible_segment, visual_length


def test_is_control_detects_c0_and_c1() -> None:
    assert is_control("\x00") is True
    assert is_control("\x7f") is True
    assert is_control("a") is False


def test_visible_segment_zero_width_returns_empty() -> None:
    assert visible_segment("hello", 0, 0, 4) == ""


def test_visual_length_expands_tabs() -> None:
    assert visual_length("\t", tab_width=4) == 4
    assert visual_length("a\tb", tab_width=4) == 5


def test_visual_length_counts_controls_as_one_column() -> None:
    assert visual_length("\x07") == 1
