"""Search state and match navigation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .buffer import TextBuffer


@dataclass(frozen=True)
class SearchMatch:
    row: int
    col: int
    length: int


@dataclass
class SearchState:
    query: str = ""
    matches: list[SearchMatch] = field(default_factory=list)
    current_index: int = -1
    case_sensitive: bool = False

    @property
    def current(self) -> SearchMatch | None:
        if 0 <= self.current_index < len(self.matches):
            return self.matches[self.current_index]
        return None


def find_matches(buffer: TextBuffer, query: str, case_sensitive: bool = False) -> list[SearchMatch]:
    if query == "":
        return []
    needle = query if case_sensitive else query.lower()
    matches: list[SearchMatch] = []
    for row, line in enumerate(buffer.lines):
        haystack = line if case_sensitive else line.lower()
        start = 0
        while True:
            col = haystack.find(needle, start)
            if col == -1:
                break
            matches.append(SearchMatch(row, col, len(query)))
            start = col + max(1, len(needle))
    return matches


def index_at_or_after(matches: list[SearchMatch], row: int, col: int) -> int:
    """Return the index of the first match at or after (row, col), or -1."""

    for index, match in enumerate(matches):
        if (match.row, match.col) >= (row, col):
            return index
    return -1


def move_match(state: SearchState, direction: int) -> SearchMatch | None:
    if not state.matches:
        state.current_index = -1
        return None
    if state.current_index < 0:
        state.current_index = 0 if direction > 0 else len(state.matches) - 1
        return state.current
    state.current_index = (state.current_index + direction) % len(state.matches)
    return state.current
