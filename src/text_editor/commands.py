"""Named editor commands used by key bindings and command mode."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import cursor as cursor_ops
from .buffer import Position, TextBuffer
from .command_parser import CommandRequest
from .config import set_config_value
from .errors import EditorError
from .fileio import read_text_file, write_text_file_atomic
from .search import SearchState, find_matches, index_at_or_after, move_match
from .state import EditorState
from .undo import DeleteEdit, InsertEdit

CommandFunc = Callable[[EditorState], None]


def _record_insert(state: EditorState, start: Position, text: str, kind: str) -> None:
    after = (state.cursor_row, state.cursor_col)
    edit = InsertEdit(start, text, start, after, kind=kind)
    state.undo_history.record(edit)


def _record_delete(
    state: EditorState,
    start: Position,
    text: str,
    before_cursor: Position,
    after_cursor: Position,
) -> None:
    edit = DeleteEdit(start, text, before_cursor, after_cursor)
    state.undo_history.record(edit)


def _finish_edit(state: EditorState) -> None:
    # An edit always dirties the buffer; the O(file-size) text comparison is
    # deferred to undo/redo and save, where returning to the saved content
    # actually needs to clear the modified indicator.
    state.dirty = True
    state.quit_warning_armed = False
    state.clear_search()
    state.ensure_cursor_visible()


def _move(state: EditorState, next_cursor: cursor_ops.Cursor) -> None:
    state.apply_cursor(next_cursor)
    state.undo_history.break_group()


def move_left(state: EditorState) -> None:
    _move(state, cursor_ops.move_left(state.buffer, state.cursor()))


def move_right(state: EditorState) -> None:
    _move(state, cursor_ops.move_right(state.buffer, state.cursor()))


def move_up(state: EditorState) -> None:
    _move(state, cursor_ops.move_up(state.buffer, state.cursor(), state.config.tab_width))


def move_down(state: EditorState) -> None:
    _move(state, cursor_ops.move_down(state.buffer, state.cursor(), state.config.tab_width))


def move_home(state: EditorState) -> None:
    _move(state, cursor_ops.move_home(state.cursor()))


def move_end(state: EditorState) -> None:
    _move(state, cursor_ops.move_end(state.buffer, state.cursor()))


def page_up(state: EditorState) -> None:
    _move(state, cursor_ops.move_page_up(state.buffer, state.cursor(), state.content_rows, state.config.tab_width))


def page_down(state: EditorState) -> None:
    _move(state, cursor_ops.move_page_down(state.buffer, state.cursor(), state.content_rows, state.config.tab_width))


def insert_printable(state: EditorState, text: str) -> None:
    if text == "":
        return
    start = (state.cursor_row, state.cursor_col)
    row, col = state.buffer.insert_string(state.cursor_row, state.cursor_col, text)
    state.set_cursor(row, col)
    _finish_edit(state)
    kind = "typing" if "\n" not in text else "insert"
    _record_insert(state, start, text, kind)


def insert_tab(state: EditorState) -> None:
    if state.config.expand_tabs:
        width = state.config.tab_width
        visual_col = state.cursor_visual_col()
        text = " " * (width - (visual_col % width))
    else:
        text = "\t"
    insert_printable(state, text)


def insert_newline(state: EditorState) -> None:
    start = (state.cursor_row, state.cursor_col)
    row, col = state.buffer.split_line(state.cursor_row, state.cursor_col)
    state.set_cursor(row, col)
    _finish_edit(state)
    state.undo_history.break_group()
    _record_insert(state, start, "\n", "newline")


def backspace(state: EditorState) -> None:
    before_cursor = (state.cursor_row, state.cursor_col)
    deleted = state.buffer.delete_before(state.cursor_row, state.cursor_col)
    if deleted is None:
        return
    start, text, after_cursor = deleted
    state.set_cursor(*after_cursor)
    _finish_edit(state)
    state.undo_history.break_group()
    _record_delete(state, start, text, before_cursor, after_cursor)


def delete_forward(state: EditorState) -> None:
    before_cursor = (state.cursor_row, state.cursor_col)
    deleted = state.buffer.delete_at(state.cursor_row, state.cursor_col)
    if deleted is None:
        return
    start, text, after_cursor = deleted
    state.set_cursor(*after_cursor)
    _finish_edit(state)
    state.undo_history.break_group()
    _record_delete(state, start, text, before_cursor, after_cursor)


def undo(state: EditorState) -> None:
    if state.undo_history.undo(state):
        state.set_status("undone")
    else:
        state.set_status("nothing to undo")


def redo(state: EditorState) -> None:
    if state.undo_history.redo(state):
        state.set_status("redone")
    else:
        state.set_status("nothing to redo")


def save(state: EditorState) -> bool:
    if state.path is None:
        state.set_status("no filename; use :saveas PATH")
        return False
    if not state.dirty:
        state.set_status("already saved")
        return True
    try:
        write_text_file_atomic(state.path, state.buffer, state.config)
    except EditorError as exc:
        state.set_status(exc.message)
        return False
    state.mark_saved()
    state.set_status(f"saved {state.path}")
    return True


def save_as(state: EditorState, path_text: str) -> bool:
    path = Path(path_text).expanduser()
    if state.path is not None and path == state.path and not state.dirty:
        state.set_status("already saved")
        return True
    try:
        write_text_file_atomic(path, state.buffer, state.config)
    except EditorError as exc:
        state.set_status(exc.message)
        return False
    state.path = path
    state.mark_saved()
    state.set_status(f"saved {path}")
    return True


def quit_editor(state: EditorState, force: bool = False) -> None:
    if state.dirty and not force:
        if state.quit_warning_armed:
            state.should_quit = True
            return
        state.quit_warning_armed = True
        state.set_status("no write since change; press Ctrl-Q again or use :quit!")
        return
    state.should_quit = True


def open_path(state: EditorState, path_text: str) -> bool:
    if state.dirty:
        state.set_status("no write since change; save before opening another file")
        return False
    path = Path(path_text).expanduser()
    if not path.exists():
        replace_buffer(state, TextBuffer(), path)
        state.set_status(f"new file: {path}")
        return True
    try:
        buffer = read_text_file(path)
    except EditorError as exc:
        state.set_status(exc.message)
        return False
    replace_buffer(state, buffer, path)
    state.set_status(f"opened {path}")
    return True


def replace_buffer(state: EditorState, buffer: TextBuffer, path: Path | None) -> None:
    state.buffer = buffer
    state.path = path
    state.saved_text = buffer.to_text()
    state.cursor_row = 0
    state.cursor_col = 0
    state.sticky_col = None
    state.viewport_row = 0
    state.viewport_col = 0
    state.recompute_dirty()
    state.undo_history.clear()
    state.clear_search()
    state.quit_warning_armed = False
    state.ensure_cursor_visible()


def find_query(state: EditorState, query: str, anchor: Position | None = None) -> bool:
    matches = find_matches(state.buffer, query, state.config.search_case_sensitive)
    search_state = SearchState(query, matches, -1, state.config.search_case_sensitive)
    if matches:
        # Search from the anchor (where the search started) so incremental typing
        # does not drag the "next match" forward as the cursor jumps.
        from_row, from_col = anchor if anchor is not None else (state.cursor_row, state.cursor_col)
        search_state.current_index = index_at_or_after(matches, from_row, from_col)
        match = search_state.current
        if match is not None:
            state.set_cursor(match.row, match.col, state.sticky_col)
            state.set_status(f"{len(matches)} match{'es' if len(matches) != 1 else ''}")
        else:
            state.set_status(f"not found: {query}")
    else:
        state.set_status(f"not found: {query}")
    state.search_state = search_state
    state.undo_history.break_group()
    return search_state.current is not None


def find_next(state: EditorState) -> None:
    if not state.search_state.query:
        state.set_status("no active search")
        return
    match = move_match(state.search_state, 1)
    if match is None:
        state.set_status(f"not found: {state.search_state.query}")
        return
    state.set_cursor(match.row, match.col, state.sticky_col)
    state.set_status(f"match {state.search_state.current_index + 1}/{len(state.search_state.matches)}")
    state.undo_history.break_group()


def find_previous(state: EditorState) -> None:
    if not state.search_state.query:
        state.set_status("no active search")
        return
    match = move_match(state.search_state, -1)
    if match is None:
        state.set_status(f"not found: {state.search_state.query}")
        return
    state.set_cursor(match.row, match.col, state.sticky_col)
    state.set_status(f"match {state.search_state.current_index + 1}/{len(state.search_state.matches)}")
    state.undo_history.break_group()


def goto_line(state: EditorState, line_text: str) -> bool:
    try:
        line_number = int(line_text)
    except ValueError:
        state.set_status("goto requires an integer line number")
        return False
    row = max(0, min(line_number - 1, state.buffer.line_count - 1))
    state.set_cursor(row, 0)
    state.set_status(f"line {row + 1}")
    state.undo_history.break_group()
    return True


def _refresh_active_search(state: EditorState) -> None:
    query = state.search_state.query
    if not query:
        return
    matches = find_matches(state.buffer, query, state.config.search_case_sensitive)
    state.search_state.matches = matches
    state.search_state.case_sensitive = state.config.search_case_sensitive
    if matches:
        state.search_state.current_index = index_at_or_after(
            matches, state.cursor_row, state.cursor_col
        )
    else:
        state.search_state.current_index = -1


def set_options(state: EditorState, options: dict[str, str]) -> bool:
    for key, value in options.items():
        try:
            state.config = set_config_value(state.config, key, value)
        except ValueError as exc:
            state.set_status(str(exc))
            return False
    _refresh_active_search(state)
    state.ensure_cursor_visible()
    state.set_status("settings updated")
    return True


def show_help(state: EditorState) -> None:
    state.set_status("^S save  ^Q quit  ^F find  ^N/^B search  ^P command  ^Z/^Y undo/redo")


def execute_command_request(state: EditorState, request: CommandRequest) -> bool:
    if request.errors:
        state.set_status("; ".join(request.errors))
        return False
    if request.command is None:
        state.set_status("empty command")
        return False

    command = request.command
    args = request.args
    if command == "open":
        return open_path(state, args[0])
    if command == "write":
        return save(state)
    if command == "saveas":
        return save_as(state, args[0])
    if command == "quit":
        quit_editor(state)
        return state.should_quit
    if command == "quit!":
        quit_editor(state, force=True)
        return True
    if command == "wq":
        if state.path is None:
            if state.dirty:
                state.set_status("no filename; use :saveas PATH then :wq")
                return False
        elif state.dirty and not save(state):
            return False
        quit_editor(state, force=True)
        return True
    if command == "find":
        return find_query(state, args[0])
    if command == "next":
        find_next(state)
        return True
    if command == "prev":
        find_previous(state)
        return True
    if command == "goto":
        return goto_line(state, args[0])
    if command == "set":
        return set_options(state, request.options)
    if command == "help":
        show_help(state)
        return True

    state.set_status(f"unknown command: {command}")
    return False


KEY_COMMANDS: dict[str, CommandFunc] = {
    "move_left": move_left,
    "move_right": move_right,
    "move_up": move_up,
    "move_down": move_down,
    "move_home": move_home,
    "move_end": move_end,
    "page_up": page_up,
    "page_down": page_down,
    "insert_newline": insert_newline,
    "backspace": backspace,
    "delete_forward": delete_forward,
    "insert_tab": insert_tab,
    "undo": undo,
    "redo": redo,
    "quit": quit_editor,
    "find_next": find_next,
    "find_previous": find_previous,
    "help": show_help,
}
