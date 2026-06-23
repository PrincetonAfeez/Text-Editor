from pathlib import Path

from text_editor.app import create_initial_state
from text_editor.buffer import TextBuffer
from text_editor.command_parser import parse_command
from text_editor.commands import execute_command_request, find_query, insert_printable, insert_tab, quit_editor
from text_editor.config import EditorConfig
from text_editor.state import EditorState


def _run(state: EditorState, command: str) -> bool:
    return execute_command_request(state, parse_command(command))


def test_write_saves_existing_path(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("old\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("old\n"), path=path)
    insert_printable(state, "N")

    assert _run(state, ":w") is True
    assert path.read_text(encoding="utf-8") == state.buffer.to_text()
    assert state.dirty is False


def test_saveas_sets_path_and_writes(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    state = EditorState(buffer=TextBuffer.from_text("body"))

    assert _run(state, f':saveas "{target}"') is True
    assert state.path == target
    assert target.read_text(encoding="utf-8") == state.buffer.to_text()


def test_open_replaces_buffer_when_clean(tmp_path: Path) -> None:
    source = tmp_path / "src.txt"
    source.write_text("from disk\n", encoding="utf-8")
    state = EditorState()

    assert _run(state, f':open "{source}"') is True
    assert state.buffer.to_text() == "from disk\n"
    assert state.path == source


def test_open_refuses_to_discard_unsaved_changes(tmp_path: Path) -> None:
    source = tmp_path / "src.txt"
    source.write_text("from disk\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("scratch"))
    insert_printable(state, "!")

    assert _run(state, f':open "{source}"') is False
    assert state.buffer.to_text() == "!scratch"


def test_wq_writes_then_quits(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    state = EditorState(buffer=TextBuffer.from_text("text"), path=path)
    insert_printable(state, "Z")

    assert _run(state, ":wq") is True
    assert state.should_quit is True
    assert path.read_text(encoding="utf-8") == state.buffer.to_text()


def test_wq_on_unnamed_dirty_buffer_reports_and_does_not_quit() -> None:
    state = EditorState()
    insert_printable(state, "z")

    assert _run(state, ":wq") is False
    assert state.should_quit is False
    assert "saveas" in state.status_message


def test_goto_moves_to_line_start_and_clamps() -> None:
    state = EditorState(buffer=TextBuffer(["hello", "world", "again"]))
    state.set_cursor(0, 4)  # a non-zero column

    assert _run(state, ":goto 2") is True
    assert (state.cursor_row, state.cursor_col) == (1, 0)  # lands at column 0

    assert _run(state, ":goto 999") is True
    assert state.cursor_row == 2  # clamps to the last line


def test_set_updates_config_and_reports_invalid_value() -> None:
    state = EditorState()

    assert _run(state, ":set tab_width=8") is True
    assert state.config.tab_width == 8

    assert _run(state, ":set tab_width=99") is False
    assert state.config.tab_width == 8  # unchanged on rejection


def test_insert_tab_expands_to_spaces_or_keeps_literal() -> None:
    expand = EditorState(config=EditorConfig(expand_tabs=True, tab_width=4))
    insert_tab(expand)
    assert expand.buffer.lines == ["    "]

    literal = EditorState(config=EditorConfig(expand_tabs=False))
    insert_tab(literal)
    assert literal.buffer.lines == ["\t"]


def test_command_errors_are_reported_not_raised() -> None:
    state = EditorState()
    assert _run(state, ":goto abc") is False
    assert "integer" in state.status_message


def test_unknown_keymap_in_config_warns_at_startup(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[editor]\nkeymap_name = "vim"\n', encoding="utf-8")

    state = create_initial_state(["--config", str(cfg)])

    assert "unknown keymap" in state.status_message


def test_open_directory_reports_not_a_regular_file(tmp_path: Path) -> None:
    state = EditorState()

    assert _run(state, f':open "{tmp_path}"') is False
    assert "not a regular file" in state.status_message


def test_write_skips_clean_file_without_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("saved\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("saved\n"), path=path)
    state.mark_saved()
    mtime = path.stat().st_mtime_ns

    assert _run(state, ":write") is True
    assert "already saved" in state.status_message
    assert path.read_text(encoding="utf-8") == "saved\n"
    assert path.stat().st_mtime_ns == mtime


def test_open_of_unreadable_existing_file_drops_the_path(tmp_path: Path) -> None:
    # Regression: an existing-but-undecodable file must not keep its path, or a
    # later save would truncate the original to zero bytes.
    bad = tmp_path / "data.bin"
    bad.write_bytes(b"\xff\xfe\x00valuable\xff")

    state = create_initial_state([str(bad)])

    assert state.path is None
    assert "decode" in state.status_message


def test_open_missing_path_creates_new_buffer(tmp_path: Path) -> None:
    target = tmp_path / "new.txt"
    state = EditorState()

    assert _run(state, f':open "{target}"') is True
    assert state.path == target
    assert state.buffer.to_text() == ""
    assert "new file" in state.status_message


def test_set_search_case_sensitive_refreshes_matches() -> None:
    state = EditorState(buffer=TextBuffer(["alpha", "ALPHA"]))
    assert find_query(state, "alpha") is True
    assert len(state.search_state.matches) == 2

    assert _run(state, ":set search_case_sensitive=true") is True
    assert len(state.search_state.matches) == 1


def test_quit_on_dirty_buffer_returns_false_until_confirmed() -> None:
    state = EditorState(buffer=TextBuffer.from_text("dirty"))
    insert_printable(state, "!")

    assert _run(state, ":quit") is False
    assert state.should_quit is False
    assert state.quit_warning_armed is True

    quit_editor(state, force=True)
    assert state.should_quit is True


def test_wq_quits_clean_named_file_without_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("saved\n", encoding="utf-8")
    state = EditorState(buffer=TextBuffer.from_text("saved\n"), path=path)
    state.mark_saved()
    mtime = path.stat().st_mtime_ns

    assert _run(state, ":wq") is True
    assert state.should_quit is True
    assert path.read_text(encoding="utf-8") == "saved\n"
    assert path.stat().st_mtime_ns == mtime


def test_set_rejects_unknown_keymap_name() -> None:
    state = EditorState()

    assert _run(state, ":set keymap_name=vim") is False
    assert state.config.keymap_name == "default"
    assert "unknown keymap" in state.status_message
