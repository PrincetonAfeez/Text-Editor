"""Tests for text_editor.app """

from __future__ import annotations

import curses
import sys
from pathlib import Path

import pytest

from text_editor.app import CursesApp, build_arg_parser, create_initial_state, main, run_curses
from text_editor.buffer import TextBuffer
from text_editor.state import EditorState, Mode
from tests.helpers import FakeScreen


def test_build_arg_parser_has_expected_options() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(["notes.txt", "--config", "cfg.toml"])
    assert args.file == "notes.txt"
    assert args.config == Path("cfg.toml")


def test_create_initial_state_opens_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("hello\n", encoding="utf-8")

    state = create_initial_state([str(path)])

    assert state.path == path
    assert state.buffer.to_text() == "hello\n"


def test_create_initial_state_reports_new_file(tmp_path: Path) -> None:
    path = tmp_path / "new.txt"

    state = create_initial_state([str(path)])

    assert state.path == path
    assert "new file" in state.status_message


def test_create_initial_state_loads_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("[editor]\ntab_width = 2\n", encoding="utf-8")
    file_path = tmp_path / "note.txt"
    file_path.write_text("x", encoding="utf-8")

    state = create_initial_state(["--config", str(cfg), str(file_path)])

    assert state.config.tab_width == 2


def test_decode_key_handles_unknown_types() -> None:
    app = CursesApp(FakeScreen(10, 40), EditorState())
    assert app.decode_key(99999) == "KEY_99999"
    assert app.decode_key(8) == "BACKSPACE"
    assert app.decode_key(None) == ""


def test_handle_key_routes_all_keymap_commands() -> None:
    state = EditorState(buffer=TextBuffer.from_text("hello\n"))
    app = CursesApp(FakeScreen(10, 40), state)

    for key in ("UP", "DOWN", "HOME", "END", "PAGE_UP", "PAGE_DOWN", "DELETE", "TAB"):
        app.handle_key(key)

    assert state.buffer.line_count >= 1


def test_handle_key_unknown_binding_is_ignored() -> None:
    state = EditorState()
    app = CursesApp(FakeScreen(10, 40), state)
    before = state.buffer.to_text()
    app.handle_key("F999")
    assert state.buffer.to_text() == before


def test_handle_key_find_prompt_cancelled() -> None:
    state = EditorState(buffer=TextBuffer(["find me"]))
    state.set_cursor(0, 0)
    screen = FakeScreen(10, 40, keys=["\x1b"])
    app = CursesApp(screen, state)
    app.handle_key("CTRL_F")
    assert state.mode == Mode.EDIT
    assert (state.cursor_row, state.cursor_col) == (0, 0)


def test_handle_key_find_prompt_accepts_query() -> None:
    state = EditorState(buffer=TextBuffer(["find me"]))
    screen = FakeScreen(10, 40, keys=["f", "\n"])
    app = CursesApp(screen, state)
    app.handle_key("CTRL_F")
    assert state.search_state.query == "f"


def test_handle_key_command_prompt_runs_command(tmp_path: Path) -> None:
    path = tmp_path / "out.txt"
    state = EditorState(buffer=TextBuffer.from_text("data"))
    screen = FakeScreen(10, 40, keys=[f':saveas "{path}"', "\n"])
    app = CursesApp(screen, state)
    app.handle_key("CTRL_P")
    assert state.path == path


def test_handle_key_save_prompt_when_unnamed(tmp_path: Path) -> None:
    path = tmp_path / "saved.txt"
    state = EditorState(buffer=TextBuffer.from_text("data"))
    insert_dirty = "x"
    state.buffer.insert_string(0, 0, insert_dirty)
    state.dirty = True
    screen = FakeScreen(10, 40, keys=[str(path), "\n"])
    app = CursesApp(screen, state)
    app.handle_key("CTRL_S")
    assert path.read_text(encoding="utf-8") == state.buffer.to_text()


def test_run_exits_immediately_when_should_quit() -> None:
    state = EditorState(should_quit=True)
    app = CursesApp(FakeScreen(10, 40), state)
    assert app.run() == 0


def test_run_handles_resize_and_input_error() -> None:
    state = EditorState()
    screen = FakeScreen(10, 40, keys=[curses.error(), curses.KEY_RESIZE, "\x11"])
    app = CursesApp(screen, state)
    assert app.run() == 0


def test_run_tolerates_curses_setup_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    state = EditorState(should_quit=True)
    app = CursesApp(FakeScreen(10, 40), state)

    def fail_curs_set(_visibility: int) -> None:
        raise curses.error()

    def fail_use_default_colors() -> None:
        raise curses.error()

    monkeypatch.setattr(curses, "curs_set", fail_curs_set)
    monkeypatch.setattr(curses, "use_default_colors", fail_use_default_colors)
    assert app.run() == 0


def test_run_curses_uses_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    state = EditorState(should_quit=True)
    seen: list[EditorState] = []

    def fake_wrapper(func):  # type: ignore[no-untyped-def]
        seen.append(state)
        return func(FakeScreen(10, 40))

    monkeypatch.setattr(curses, "wrapper", fake_wrapper)
    assert run_curses(state) == 0
    assert seen


def test_run_curses_without_curses_module(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import builtins

    real_import = builtins.__import__
    monkeypatch.delitem(sys.modules, "curses", raising=False)

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "curses":
            raise ModuleNotFoundError("no curses")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = run_curses(EditorState())
    captured = capsys.readouterr()
    assert result == 1
    assert "windows-curses" in captured.err


def test_main_delegates_to_run_curses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("text_editor.app.run_curses", lambda _state: 7)
    assert main([]) == 7


def test_main_returns_parser_exit_code() -> None:
    assert main(["--not-a-real-flag"]) == 2
