"""Tests for text_editor.search """

from text_editor.buffer import TextBuffer
from text_editor.commands import find_next, find_previous, find_query
from text_editor.search import find_matches, index_at_or_after
from text_editor.state import EditorState


def test_find_matches_all_lines() -> None:
    buffer = TextBuffer(["alpha", "beta alpha", "ALPHA"])

    matches = find_matches(buffer, "alpha", case_sensitive=False)

    assert [(match.row, match.col) for match in matches] == [(0, 0), (1, 5), (2, 0)]


def test_find_matches_case_sensitive_excludes_other_casings() -> None:
    buffer = TextBuffer(["alpha", "beta alpha", "ALPHA"])

    matches = find_matches(buffer, "alpha", case_sensitive=True)

    assert [(match.row, match.col) for match in matches] == [(0, 0), (1, 5)]


def test_find_navigation_wraps() -> None:
    state = EditorState(buffer=TextBuffer(["one two one"]))

    assert find_query(state, "one")
    assert (state.cursor_row, state.cursor_col) == (0, 0)

    find_next(state)
    assert (state.cursor_row, state.cursor_col) == (0, 8)

    find_next(state)
    assert (state.cursor_row, state.cursor_col) == (0, 0)

    find_previous(state)
    assert (state.cursor_row, state.cursor_col) == (0, 8)


def test_index_at_or_after_does_not_wrap_backward() -> None:
    buffer = TextBuffer(["aaa", "bbb aaa", "ccc"])
    matches = find_matches(buffer, "aaa")

    assert index_at_or_after(matches, 2, 0) == -1
    assert index_at_or_after(matches, 1, 6) == -1
    assert index_at_or_after(matches, 1, 4) == 1


def test_find_query_stays_put_when_no_forward_match() -> None:
    state = EditorState(buffer=TextBuffer(["aaa", "bbb aaa", "ccc"]))
    state.set_cursor(2, 0)

    assert find_query(state, "aaa", anchor=(2, 0)) is False
    assert (state.cursor_row, state.cursor_col) == (2, 0)
    assert state.search_state.current is None
    assert "not found" in state.status_message


def test_find_previous_from_unset_index_goes_to_last_match() -> None:
    state = EditorState(buffer=TextBuffer(["aaa", "bbb aaa", "ccc"]))
    state.set_cursor(2, 0)
    find_query(state, "aaa", anchor=(2, 0))
    assert state.search_state.current_index == -1

    find_previous(state)
    assert state.search_state.current_index == 1
    assert (state.cursor_row, state.cursor_col) == (1, 4)


def test_search_navigation_preserves_sticky_column() -> None:
    state = EditorState(buffer=TextBuffer(["aaa", "bbb aaa", "ccc"]))
    state.set_cursor(0, 0, sticky_col=5)
    find_query(state, "aaa", anchor=(0, 0))

    assert state.sticky_col == 5
