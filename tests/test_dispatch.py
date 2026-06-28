"""Tests for app key dispatch without a live curses terminal 

``handle_key`` never touches curses or ``self.stdscr`` (only ``self.renderer``),
so these tests build a ``CursesApp`` via ``object.__new__`` and inject a fake
renderer. That keeps the dispatch layer testable on machines without curses.
"""

from __future__ import annotations

import curses  # the fake installed by tests/conftest.py
from pathlib import Path

import pytest

from text_editor.app import CursesApp
from text_editor.buffer import TextBuffer
from text_editor.commands import KEY_COMMANDS, insert_printable
from text_editor.config import EditorConfig
from text_editor.keymap import default_keymap, keymap_for
from text_editor.state import EditorState


class FakeRenderer:
    def __init__(self, response: str | None = None) -> None:
        self.response = response
        self.prompts: list[tuple[str, str, str]] = []

    def prompt(self, state: EditorState, label: str, initial: str = "", mode: str = "command") -> str | None:
        self.prompts.append((label, initial, mode))
        return self.response


def _make_app(state: EditorState, renderer: FakeRenderer) -> CursesApp:
    app = object.__new__(CursesApp)
    app.state = state
    app.renderer = renderer  # type: ignore[assignment]
    app.curses = curses  # type: ignore[assignment]
    return app


def test_every_keymap_command_is_reachable() -> None:
    handled_in_handle_key = {"find_prompt", "command_prompt", "save"}
    for command in default_keymap().values():
        assert command in KEY_COMMANDS or command in handled_in_handle_key, command


def test_ctrl_s_saves_a_named_file(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    state = EditorState(buffer=TextBuffer.from_text("hello\n"), path=path)
    insert_printable(state, "X")
    assert state.dirty is True

    _make_app(state, FakeRenderer()).handle_key("CTRL_S")

    assert path.read_text(encoding="utf-8") == state.buffer.to_text()
    assert state.dirty is False


def test_ctrl_s_skips_clean_file_without_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("hello\n"), path=path)
    state.mark_saved()
    mtime = path.stat().st_mtime_ns

    _make_app(state, FakeRenderer()).handle_key("CTRL_S")

    assert "already saved" in state.status_message
    assert path.stat().st_mtime_ns == mtime


def test_ctrl_s_without_a_path_prompts_save_as(tmp_path: Path) -> None:
    target = tmp_path / "fresh.txt"
    state = EditorState(buffer=TextBuffer.from_text("data"))
    app = _make_app(state, FakeRenderer(response=str(target)))

    app.handle_key("CTRL_S")

    assert app.renderer.prompts and app.renderer.prompts[0][0] == "Save as: "  # type: ignore[attr-defined]
    assert target.read_text(encoding="utf-8") == state.buffer.to_text()
    assert state.path == target


def test_any_action_cancels_a_pending_quit_warning() -> None:
    state = EditorState(buffer=TextBuffer.from_text("ab"))
    insert_printable(state, "x")  # make the buffer dirty
    app = _make_app(state, FakeRenderer())

    app.handle_key("CTRL_Q")
    assert state.quit_warning_armed is True

    app.handle_key("LEFT")  # navigating cancels the pending quit
    assert state.quit_warning_armed is False

    app.handle_key("CTRL_Q")  # so this is only the first press again
    assert state.should_quit is False
    assert state.quit_warning_armed is True


def test_printable_key_inserts_text() -> None:
    state = EditorState()
    _make_app(state, FakeRenderer()).handle_key("a")
    assert state.buffer.to_text() == "a"
    assert state.dirty is True


def test_decode_key_maps_controls_specials_and_printables() -> None:
    app = _make_app(EditorState(), FakeRenderer())
    fc = app.curses  # type: ignore[attr-defined]

    # control characters
    assert app.decode_key("\x13") == "CTRL_S"
    assert app.decode_key("\x01") == "CTRL_A"
    # special string keys decoded before the control range
    assert app.decode_key("\t") == "TAB"
    assert app.decode_key("\n") == "ENTER"
    assert app.decode_key("\r") == "ENTER"
    assert app.decode_key("\x7f") == "BACKSPACE"
    assert app.decode_key("\x08") == "BACKSPACE"
    # printable characters pass through unchanged
    assert app.decode_key("a") == "a"
    assert app.decode_key(" ") == " "
    # curses integer key codes
    assert app.decode_key(fc.KEY_LEFT) == "LEFT"
    assert app.decode_key(fc.KEY_DC) == "DELETE"
    assert app.decode_key(fc.KEY_RESIZE) == "RESIZE"
    assert app.decode_key(fc.KEY_BACKSPACE) == "BACKSPACE"
    # unknown integer codes fall through to a stable name
    assert app.decode_key(99999) == "KEY_99999"


def test_keymap_follows_config_on_each_keypress(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def tracking_keymap(name: str) -> dict[str, str]:
        seen.append(name)
        return keymap_for(name)

    monkeypatch.setattr("text_editor.app.keymap_for", tracking_keymap)
    state = EditorState(config=EditorConfig(keymap_name="default"))
    app = _make_app(state, FakeRenderer())

    app.handle_key("LEFT")
    state.config = EditorConfig(keymap_name="unknown")
    app.handle_key("LEFT")

    assert seen == ["default", "unknown"]
