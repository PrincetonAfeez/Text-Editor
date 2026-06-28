"""Additional render and prompt coverage """

from __future__ import annotations

import curses

import pytest

from text_editor.buffer import TextBuffer
from text_editor.render import CursesRenderer
from text_editor.state import EditorState, Mode
from tests.helpers import FakeScreen


def test_prompt_ctrl_u_clears_text() -> None:
    state = EditorState()
    screen = FakeScreen(8, 40, keys=["\x15", "\n"])  # Ctrl-U clears, Enter accepts
    result = CursesRenderer(screen).prompt(state, ":", initial="delete me")
    assert result == ""
    assert state.mode == Mode.EDIT


def test_prompt_ignores_non_printable_keys() -> None:
    state = EditorState()
    screen = FakeScreen(8, 40, keys=["\x00", "x", "\n"])
    result = CursesRenderer(screen).prompt(state, ":", initial="")
    assert result == "x"


def test_prompt_handles_get_wch_error_then_enter() -> None:
    state = EditorState()
    screen = FakeScreen(8, 40, keys=[curses.error(), "ok", "\n"])
    assert CursesRenderer(screen).prompt(state, "Find: ") == "ok"


def test_place_cursor_tolerates_move_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    state = EditorState(buffer=TextBuffer(["hello"]))
    screen = FakeScreen(3, 5)

    def fail_move(_y: int, _x: int) -> None:
        raise curses.error()

    monkeypatch.setattr(screen, "move", fail_move)
    CursesRenderer(screen).draw(state)  # should not raise


def test_draw_shows_prompt_in_command_mode() -> None:
    state = EditorState(mode=Mode.COMMAND, prompt_label=":", prompt_text="write")
    screen = FakeScreen(6, 20)
    CursesRenderer(screen).draw(state)
    assert ":write" in screen.row_text(5)
