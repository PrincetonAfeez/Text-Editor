"""Editor state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from .buffer import TextBuffer
from .config import EditorConfig
from .cursor import Cursor
from .search import SearchState
from .undo import UndoHistory
from .viewport import Viewport, ensure_visible


class Mode(StrEnum):
    """The interaction mode the editor is currently in."""

    EDIT = "edit"
    COMMAND = "command"
    SEARCH = "search"


@dataclass
class EditorState:
    buffer: TextBuffer = field(default_factory=TextBuffer)
    config: EditorConfig = field(default_factory=EditorConfig)
    path: Path | None = None
    cursor_row: int = 0
    cursor_col: int = 0
    sticky_col: int | None = None
    viewport_row: int = 0
    viewport_col: int = 0
    screen_rows: int = 24
    screen_cols: int = 80
    dirty: bool = False
    saved_text: str = ""
    status_message: str = ""
    should_quit: bool = False
    quit_warning_armed: bool = False
    mode: Mode = Mode.EDIT
    prompt_label: str = ""
    prompt_text: str = ""
    undo_history: UndoHistory = field(default_factory=UndoHistory)
    search_state: SearchState = field(default_factory=SearchState)

    def __post_init__(self) -> None:
        if self.saved_text == "":
            self.saved_text = self.buffer.to_text()
        self.recompute_dirty()

    @property
    def filename(self) -> str:
        return self.path.name if self.path else "[No Name]"

    @property
    def content_rows(self) -> int:
        return max(1, self.screen_rows - 2)

    @property
    def content_cols(self) -> int:
        return max(1, self.screen_cols)

    def resize(self, rows: int, cols: int) -> None:
        self.screen_rows = max(1, rows)
        self.screen_cols = max(1, cols)
        self.ensure_cursor_visible()

    def cursor(self) -> Cursor:
        return Cursor(self.cursor_row, self.cursor_col, self.sticky_col)

    def set_cursor(self, row: int, col: int, sticky_col: int | None = None) -> None:
        row, col = self.buffer.clamp_position(row, col)
        self.cursor_row = row
        self.cursor_col = col
        self.sticky_col = sticky_col
        self.ensure_cursor_visible()

    def apply_cursor(self, cursor: Cursor) -> None:
        self.set_cursor(cursor.row, cursor.col, cursor.sticky_col)

    def cursor_visual_col(self) -> int:
        return self.buffer.visual_col(self.cursor_row, self.cursor_col, self.config.tab_width)

    def ensure_cursor_visible(self) -> None:
        viewport = ensure_visible(
            Viewport(self.viewport_row, self.viewport_col),
            self.cursor_row,
            self.cursor_visual_col(),
            self.content_rows,
            self.content_cols,
        )
        self.viewport_row = viewport.row_offset
        self.viewport_col = viewport.col_offset

    def recompute_dirty(self) -> None:
        self.dirty = self.buffer.to_text() != self.saved_text

    def mark_saved(self) -> None:
        self.saved_text = self.buffer.to_text()
        self.recompute_dirty()
        self.quit_warning_armed = False

    def set_status(self, message: str) -> None:
        self.status_message = message

    def clear_search(self) -> None:
        self.search_state = SearchState(case_sensitive=self.config.search_case_sensitive)
