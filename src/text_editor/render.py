"""Thin curses drawing adapter."""

from __future__ import annotations

import curses
from collections.abc import Callable

from .display import visible_segment, visual_length
from .state import EditorState, Mode


def _safe_addstr(window: curses.window, row: int, col: int, text: str, attr: int = 0) -> None:
    try:
        window.addstr(row, col, text, attr)
    except curses.error:
        pass


def _ctrl_name(char: str) -> str | None:
    if len(char) == 1 and 1 <= ord(char) <= 26:
        return f"CTRL_{chr(ord(char) + 64)}"
    return None


class CursesRenderer:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr

    def draw(self, state: EditorState) -> None:
        height, width = self.stdscr.getmaxyx()
        state.resize(height, width)
        self.stdscr.erase()

        if height < 3 or width < 10:
            _safe_addstr(self.stdscr, 0, 0, "Terminal too small"[: max(0, width - 1)])
            self.stdscr.refresh()
            return

        self._draw_buffer(state)
        self._draw_status(state)
        self._draw_message(state)
        self._place_cursor(state)
        self.stdscr.noutrefresh()
        curses.doupdate()

    def _draw_buffer(self, state: EditorState) -> None:
        width = state.screen_cols
        tab_width = state.config.tab_width
        viewport_col = state.viewport_col
        current_match = state.search_state.current
        for screen_row in range(state.content_rows):
            buffer_row = state.viewport_row + screen_row
            if buffer_row >= state.buffer.line_count:
                _safe_addstr(self.stdscr, screen_row, 0, "~".ljust(width)[:width])
                continue

            line = state.buffer.get_line(buffer_row)
            _safe_addstr(self.stdscr, screen_row, 0, visible_segment(line, viewport_col, width, tab_width))

            if current_match and current_match.row == buffer_row:
                start = state.buffer.visual_col(buffer_row, current_match.col, tab_width)
                end = state.buffer.visual_col(buffer_row, current_match.col + current_match.length, tab_width)
                vis_start = max(start, viewport_col)
                vis_end = min(end, viewport_col + width)
                if vis_start < vis_end:
                    segment = visible_segment(line, vis_start, vis_end - vis_start, tab_width)
                    _safe_addstr(self.stdscr, screen_row, vis_start - viewport_col, segment, curses.A_REVERSE)

    def _draw_status(self, state: EditorState) -> None:
        modified = "*" if state.dirty else ""
        mode = state.mode.upper()
        status = (
            f" {state.filename}{modified} | {state.buffer.line_count} lines "
            f"| Ln {state.cursor_row + 1}, Col {state.cursor_visual_col() + 1} | {mode}"
        )
        if state.config.show_status_hints:
            status += " | ^S Save ^Q Quit ^P Cmd"
        row = max(0, state.screen_rows - 2)
        segment = visible_segment(status, 0, state.screen_cols, state.config.tab_width)
        _safe_addstr(self.stdscr, row, 0, segment, curses.A_REVERSE)

    def _draw_message(self, state: EditorState) -> None:
        row = max(0, state.screen_rows - 1)
        if state.mode in (Mode.COMMAND, Mode.SEARCH):
            message = f"{state.prompt_label}{state.prompt_text}"
        else:
            message = state.status_message
        segment = visible_segment(message, 0, state.screen_cols, state.config.tab_width)
        _safe_addstr(self.stdscr, row, 0, segment)

    def _place_cursor(self, state: EditorState) -> None:
        if state.mode in (Mode.COMMAND, Mode.SEARCH):
            y = max(0, state.screen_rows - 1)
            x = min(
                state.screen_cols - 1,
                visual_length(state.prompt_label + state.prompt_text, state.config.tab_width),
            )
        else:
            y = state.cursor_row - state.viewport_row
            x = state.cursor_visual_col() - state.viewport_col
            y = max(0, min(state.content_rows - 1, y))
            x = max(0, min(state.screen_cols - 1, x))
        try:
            self.stdscr.move(y, x)
        except curses.error:
            pass

    def prompt(
        self,
        state: EditorState,
        label: str,
        initial: str = "",
        mode: Mode = Mode.COMMAND,
        on_change: Callable[[str], None] | None = None,
    ) -> str | None:
        old_mode = state.mode
        old_label = state.prompt_label
        old_text = state.prompt_text
        state.mode = mode
        state.prompt_label = label
        state.prompt_text = initial
        try:
            if on_change is not None:
                on_change(state.prompt_text)
            while True:
                self.draw(state)
                try:
                    key = self.stdscr.get_wch()
                except curses.error:
                    continue
                if key in ("\n", "\r") or key == curses.KEY_ENTER:
                    return state.prompt_text
                if key == "\x1b":
                    state.set_status("cancelled")
                    return None
                if key in ("\b", "\x7f") or key == curses.KEY_BACKSPACE:
                    state.prompt_text = state.prompt_text[:-1]
                elif isinstance(key, str):
                    ctrl = _ctrl_name(key)
                    if ctrl == "CTRL_U":
                        state.prompt_text = ""
                    elif key.isprintable():
                        state.prompt_text += key
                    else:
                        continue
                else:
                    continue
                if on_change is not None:
                    on_change(state.prompt_text)
        finally:
            # Restore the prior prompt state on every exit path, including an
            # exception. The return expression is evaluated before this runs, so
            # the typed text is still returned correctly.
            state.mode = old_mode
            state.prompt_label = old_label
            state.prompt_text = old_text
