"""Curses setup, main loop, input decoding, and command dispatch """

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .buffer import TextBuffer
from .command_parser import parse_command
from .commands import KEY_COMMANDS, execute_command_request, find_query, insert_printable, save, save_as
from .config import load_config
from .errors import EditorError
from .fileio import read_text_file
from .keymap import keymap_for
from .state import EditorState, Mode

logger = logging.getLogger(__name__)


def build_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Curses-based terminal text editor.")
    parser.add_argument("file", nargs="?", help="file to open")
    parser.add_argument("--config", type=Path, help="config TOML path")
    parser.add_argument("--version", action="version", version=f"text-editor {__version__}")
    return parser


def create_initial_state(argv: Sequence[str]) -> EditorState:
    args = build_arg_parser().parse_args(argv)
    config, warnings = load_config(args.config)
    buffer = TextBuffer()
    path: Path | None = None
    status_messages = warnings[:]

    if args.file:
        path = Path(args.file).expanduser()
        if path.exists():
            try:
                buffer = read_text_file(path)
            except EditorError as exc:
                status_messages.append(exc.message)
                buffer = TextBuffer()
                # Drop the path so an accidental save cannot overwrite a file we
                # could not read (e.g. binary content or a permission error).
                path = None
        else:
            status_messages.append(f"new file: {path}")

    state = EditorState(buffer=buffer, config=config, path=path)
    state.search_state.case_sensitive = config.search_case_sensitive
    if status_messages:
        state.set_status("; ".join(status_messages))
    return state


class CursesApp:
    def __init__(self, stdscr: Any, state: EditorState) -> None:
        import curses

        from .render import CursesRenderer

        self.curses = curses
        self.stdscr = stdscr
        self.state = state
        self.renderer = CursesRenderer(stdscr)

    def run(self) -> int:
        curses = self.curses
        # curses.wrapper already applied noecho/cbreak/keypad. Raw mode supersedes
        # cbreak so control keys such as Ctrl-S, Ctrl-Q, and Ctrl-Z reach the editor
        # instead of being intercepted by terminal flow control or job control.
        curses.raw()
        self.stdscr.keypad(True)
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        try:
            curses.use_default_colors()
        except curses.error:
            pass

        while not self.state.should_quit:
            self.renderer.draw(self.state)
            try:
                key = self.stdscr.get_wch()
            except curses.error:
                # An interrupted read (e.g. EINTR on a signal) should not end the
                # session; redraw and wait for the next key.
                continue
            decoded = self.decode_key(key)
            if decoded == "RESIZE":
                self.state.ensure_cursor_visible()
                continue
            self.handle_key(decoded)
        return 0

    def decode_key(self, key: object) -> str:
        curses = self.curses
        int_keys = {
            curses.KEY_LEFT: "LEFT",
            curses.KEY_RIGHT: "RIGHT",
            curses.KEY_UP: "UP",
            curses.KEY_DOWN: "DOWN",
            curses.KEY_HOME: "HOME",
            curses.KEY_END: "END",
            curses.KEY_PPAGE: "PAGE_UP",
            curses.KEY_NPAGE: "PAGE_DOWN",
            curses.KEY_DC: "DELETE",
            curses.KEY_RESIZE: "RESIZE",
            curses.KEY_ENTER: "ENTER",
            curses.KEY_BACKSPACE: "BACKSPACE",
        }
        if isinstance(key, int):
            if key in int_keys:
                return int_keys[key]
            if key in {8, 127}:
                return "BACKSPACE"
            return f"KEY_{key}"

        if key in {"\n", "\r"}:
            return "ENTER"
        if key == "\t":
            return "TAB"
        if key in {"\b", "\x7f"}:
            return "BACKSPACE"
        if isinstance(key, str) and len(key) == 1 and 1 <= ord(key) <= 26:
            return f"CTRL_{chr(ord(key) + 64)}"
        if isinstance(key, str):
            return key
        return ""

    def handle_key(self, decoded: str) -> None:
        if len(decoded) == 1 and decoded.isprintable():
            insert_printable(self.state, decoded)
            return

        command_name = keymap_for(self.state.config.keymap_name).get(decoded)
        if command_name is None:
            return

        # Any action other than quit cancels a pending dirty-quit confirmation,
        # so the "press again" prompt only applies to the very next keypress.
        if command_name != "quit":
            self.state.quit_warning_armed = False

        if command_name == "find_prompt":
            anchor = (self.state.cursor_row, self.state.cursor_col)
            initial = self.state.search_state.query

            def live_search(text: str) -> None:
                if text:
                    find_query(self.state, text, anchor=anchor)
                else:
                    self.state.clear_search()
                    self.state.set_cursor(*anchor)

            query = self.renderer.prompt(self.state, "Find: ", initial, mode=Mode.SEARCH, on_change=live_search)
            if not query:
                # cancelled or cleared: return to where the search started
                self.state.clear_search()
                self.state.set_cursor(*anchor)
            else:
                find_query(self.state, query, anchor=anchor)
            return

        if command_name == "command_prompt":
            command_text = self.renderer.prompt(self.state, ":", mode=Mode.COMMAND)
            if command_text is not None:
                execute_command_request(self.state, parse_command(command_text))
            return

        if command_name == "save":
            if self.state.path is None:
                path = self.renderer.prompt(self.state, "Save as: ", mode=Mode.COMMAND)
                if path:
                    save_as(self.state, path)
            else:
                save(self.state)
            return

        command_func = KEY_COMMANDS.get(command_name)
        if command_func is not None:
            command_func(self.state)


def run_curses(state: EditorState) -> int:
    try:
        import curses
    except ModuleNotFoundError:
        logger.error(
            "curses is not available. On Windows, install with: pip install windows-curses"
        )
        return 1

    def wrapped(stdscr: Any) -> int:
        return CursesApp(stdscr, state).run()

    return curses.wrapper(wrapped)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        state = create_initial_state(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 1
    return run_curses(state)
