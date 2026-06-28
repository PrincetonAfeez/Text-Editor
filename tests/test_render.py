"""Headless render tests 

A fake ``curses`` is installed by ``tests/conftest.py`` so ``text_editor.render``
(which imports curses at module load) can be imported without a terminal. The
real rendering code runs unchanged against a ``FakeScreen`` that records a grid
of cells and attributes and feeds queued keys to ``prompt()``.
"""

from __future__ import annotations

import curses
from pathlib import Path

import pytest

from text_editor.buffer import TextBuffer
from text_editor.commands import find_query, insert_printable
from text_editor.config import EditorConfig
from text_editor.render import CursesRenderer
from text_editor.state import EditorState, Mode


class FakeScreen:
    """Records what would be drawn so render output can be asserted."""

    def __init__(self, height: int, width: int, keys: list[object] | None = None) -> None:
        self.height = height
        self.width = width
        self.cells = [[" "] * width for _ in range(height)]
        self.attrs = [[0] * width for _ in range(height)]
        self.cursor = (0, 0)
        self._keys = list(keys or [])

    def getmaxyx(self) -> tuple[int, int]:
        return (self.height, self.width)

    def erase(self) -> None:
        self.cells = [[" "] * self.width for _ in range(self.height)]
        self.attrs = [[0] * self.width for _ in range(self.height)]

    def addstr(self, row: int, col: int, text: str, attr: int = 0) -> None:
        if row < 0 or row >= self.height or col < 0:
            raise curses.error("addstr out of bounds")
        for offset, char in enumerate(text):
            column = col + offset
            if column >= self.width:
                raise curses.error("addstr past right edge")
            self.cells[row][column] = char
            self.attrs[row][column] = attr

    def move(self, y: int, x: int) -> None:
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            raise curses.error("move out of bounds")
        self.cursor = (y, x)

    def noutrefresh(self) -> None:
        pass

    def refresh(self) -> None:
        pass

    def get_wch(self) -> object:
        if not self._keys:
            raise curses.error("no input")
        return self._keys.pop(0)

    def row_text(self, row: int) -> str:
        return "".join(self.cells[row])


def test_buffer_rows_render_with_padding_and_tilde() -> None:
    state = EditorState(buffer=TextBuffer(["hello", "world"]))
    screen = FakeScreen(8, 20)

    CursesRenderer(screen).draw(state)

    assert screen.row_text(0).rstrip() == "hello"
    assert screen.row_text(1).rstrip() == "world"
    assert screen.row_text(2).rstrip() == "~"  # rows past end of buffer
    assert len(screen.row_text(0)) == 20  # padded to full width


def test_tab_is_expanded_in_rendered_row() -> None:
    state = EditorState(buffer=TextBuffer(["\tab"]), config=EditorConfig(tab_width=4))
    screen = FakeScreen(6, 40)

    CursesRenderer(screen).draw(state)

    assert screen.row_text(0).startswith("    ab")


def test_horizontal_scroll_slices_visible_text() -> None:
    state = EditorState(buffer=TextBuffer(["0123456789ABCDEF"]))
    state.set_cursor(0, 16)  # cursor at end of a line longer than the screen
    screen = FakeScreen(6, 10)

    CursesRenderer(screen).draw(state)

    assert state.viewport_col > 0  # scrolled right to keep the cursor visible
    assert "F" in screen.row_text(0)
    assert "0" not in screen.row_text(0)  # the start scrolled out of view


def test_status_bar_reports_filename_and_position(tmp_path: Path) -> None:
    state = EditorState(buffer=TextBuffer(["one", "two"]), path=tmp_path / "notes.txt")
    screen = FakeScreen(8, 60)

    CursesRenderer(screen).draw(state)

    status = screen.row_text(6)  # screen_rows - 2
    assert "notes.txt" in status
    assert "2 lines" in status
    assert "Ln 1, Col 1" in status
    assert "EDIT" in status
    assert screen.attrs[6][0] == curses.A_REVERSE


def test_status_bar_uses_visual_column_for_tabs() -> None:
    state = EditorState(buffer=TextBuffer(["\thello"]), config=EditorConfig(tab_width=4))
    state.set_cursor(0, 1)  # after the tab → visual column 4
    screen = FakeScreen(8, 60)

    CursesRenderer(screen).draw(state)

    assert "Col 5" in screen.row_text(6)


def test_status_bar_shows_dirty_marker() -> None:
    state = EditorState(buffer=TextBuffer(["x"]))
    insert_printable(state, "y")
    screen = FakeScreen(8, 60)

    CursesRenderer(screen).draw(state)

    assert "*" in screen.row_text(6)


def test_message_bar_shows_status_then_prompt() -> None:
    state = EditorState()
    state.set_status("saved notes.txt")
    screen = FakeScreen(8, 40)
    renderer = CursesRenderer(screen)

    renderer.draw(state)
    assert screen.row_text(7).startswith("saved notes.txt")  # screen_rows - 1

    state.mode = Mode.COMMAND
    state.prompt_label = ":"
    state.prompt_text = "wq"
    renderer.draw(state)
    assert screen.row_text(7).startswith(":wq")


def test_current_search_match_is_highlighted() -> None:
    state = EditorState(buffer=TextBuffer(["find me here"]))
    screen = FakeScreen(6, 40)
    find_query(state, "me")  # 'me' starts at column 5

    CursesRenderer(screen).draw(state)

    assert screen.attrs[0][5] == curses.A_REVERSE
    assert screen.attrs[0][6] == curses.A_REVERSE
    assert screen.attrs[0][4] == 0
    assert screen.attrs[0][7] == 0


def test_cursor_is_placed_at_logical_position() -> None:
    state = EditorState(buffer=TextBuffer(["hello world"]))
    state.set_cursor(0, 6)
    screen = FakeScreen(8, 40)

    CursesRenderer(screen).draw(state)

    assert screen.cursor == (0, 6)


def test_terminal_too_small_shows_message() -> None:
    state = EditorState()
    screen = FakeScreen(2, 30)  # height < 3

    CursesRenderer(screen).draw(state)

    assert screen.row_text(0).rstrip() == "Terminal too small"


def test_prompt_returns_typed_text_on_enter() -> None:
    state = EditorState()
    screen = FakeScreen(10, 40, keys=["w", "q", "\n"])

    result = CursesRenderer(screen).prompt(state, ":")

    assert result == "wq"
    assert state.mode == "edit"  # restored afterwards


def test_prompt_cancels_on_escape() -> None:
    state = EditorState()
    screen = FakeScreen(10, 40, keys=["a", "\x1b"])

    result = CursesRenderer(screen).prompt(state, ":")

    assert result is None
    assert state.status_message == "cancelled"


def test_prompt_editing_supports_backspace_and_clear() -> None:
    # type 'abc', backspace -> 'ab', Ctrl-U clears -> '', type 'z', Enter
    state = EditorState()
    screen = FakeScreen(10, 40, keys=["a", "b", "c", "\x7f", "\x15", "z", "\n"])

    assert CursesRenderer(screen).prompt(state, ":") == "z"


def test_prompt_ignores_a_curses_error_read() -> None:
    class FlakyScreen(FakeScreen):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            self._raised = False

        def get_wch(self) -> object:
            if not self._raised:
                self._raised = True
                raise curses.error("interrupted")
            return super().get_wch()

    state = EditorState()
    screen = FlakyScreen(10, 40, keys=["h", "i", "\n"])

    assert CursesRenderer(screen).prompt(state, ":") == "hi"


def test_prompt_on_change_fires_initially_and_per_keystroke() -> None:
    seen: list[str] = []
    state = EditorState()
    screen = FakeScreen(10, 40, keys=["a", "b", "\n"])

    CursesRenderer(screen).prompt(state, ":", on_change=lambda t: seen.append(t))

    assert seen == ["", "a", "ab"]  # initial empty text, then after each keystroke


def test_incremental_find_locates_match_while_typing() -> None:
    state = EditorState(buffer=TextBuffer(["alpha beta"]))
    screen = FakeScreen(8, 40, keys=["b", "e", "\n"])
    anchor = (0, 0)

    def live(text: str) -> None:
        if text:
            find_query(state, text, anchor=anchor)
        else:
            state.clear_search()

    CursesRenderer(screen).prompt(state, "Find: ", mode="search", on_change=live)

    assert state.search_state.query == "be"
    assert state.search_state.current is not None
    assert (state.search_state.current.row, state.search_state.current.col) == (0, 6)


def test_prompt_restores_mode_even_on_unexpected_error() -> None:
    class Boom(Exception):
        pass

    class ExplodingScreen(FakeScreen):
        def get_wch(self) -> object:
            raise Boom()

    state = EditorState()
    screen = ExplodingScreen(10, 40)

    with pytest.raises(Boom):
        CursesRenderer(screen).prompt(state, ":")
    assert state.mode == "edit"  # the finally block restored prompt state
