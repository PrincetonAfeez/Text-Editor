"""Additional search coverage """

from __future__ import annotations

from text_editor.buffer import TextBuffer
from text_editor.commands import find_query
from text_editor.search import SearchMatch, SearchState, find_matches, index_at_or_after, move_match
from text_editor.state import EditorState


def test_find_matches_empty_query() -> None:
    buffer = TextBuffer(["abc"])
    assert find_matches(buffer, "", case_sensitive=False) == []


def test_index_at_or_after_returns_minus_one_when_no_match() -> None:
    matches = [SearchMatch(0, 5, 1)]
    assert index_at_or_after(matches, 0, 0) == 0
    assert index_at_or_after(matches, 0, 6) == -1


def test_move_match_returns_none_without_matches() -> None:
    state = SearchState("needle", [], -1, False)
    assert move_match(state, 1) is None


def test_move_match_wraps_forward_and_backward() -> None:
    matches = [SearchMatch(0, 0, 1), SearchMatch(0, 4, 1)]
    state = SearchState("a", matches, 0, False)
    assert move_match(state, 1) == matches[1]
    assert move_match(state, 1) == matches[0]
    assert move_match(state, -1) == matches[1]


def test_find_query_empty_string_clears_matches() -> None:
    state = EditorState(buffer=TextBuffer(["abc"]))
    assert find_query(state, "") is False
