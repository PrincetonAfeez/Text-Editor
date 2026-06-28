"""Curses-independent text buffer operations """

from __future__ import annotations

from dataclasses import dataclass, field

from .display import char_display_width

Position = tuple[int, int]


def detect_line_ending(text: str) -> str:
    """Return the first line ending style found in text, defaulting to LF."""

    crlf = text.find("\r\n")
    lf = text.find("\n")
    cr = text.find("\r")
    candidates = [(idx, ending) for idx, ending in ((crlf, "\r\n"), (lf, "\n"), (cr, "\r")) if idx != -1]
    if not candidates:
        return "\n"
    return min(candidates, key=lambda item: item[0])[1]


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


@dataclass
class TextBuffer:
    """Editable text represented as an array of lines."""

    lines: list[str] = field(default_factory=lambda: [""])
    line_ending: str = "\n"
    trailing_newline: bool = False

    def __post_init__(self) -> None:
        if not self.lines:
            self.lines = [""]

    @classmethod
    def from_text(cls, text: str) -> TextBuffer:
        line_ending = detect_line_ending(text)
        normalized = normalize_newlines(text)
        trailing = normalized.endswith("\n")
        if normalized == "":
            return cls([""], line_ending=line_ending, trailing_newline=False)

        parts = normalized.split("\n")
        if trailing:
            parts = parts[:-1]
        return cls(parts or [""], line_ending=line_ending, trailing_newline=trailing)

    def to_text(self) -> str:
        if self.lines == [""] and not self.trailing_newline:
            return ""
        text = self.line_ending.join(self.lines)
        if self.trailing_newline:
            text += self.line_ending
        return text

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def _clamp_row(self, row: int) -> int:
        """Clamp out-of-range row indices instead of raising ``IndexError``."""

        return max(0, min(row, self.line_count - 1))

    def get_line(self, row: int) -> str:
        return self.lines[self._clamp_row(row)]

    def set_line(self, row: int, value: str) -> None:
        self.lines[self._clamp_row(row)] = value

    def clamp_position(self, row: int, col: int) -> Position:
        row = max(0, min(row, self.line_count - 1))
        col = max(0, min(col, len(self.lines[row])))
        return row, col

    def insert_char(self, row: int, col: int, char: str) -> Position:
        if len(char) != 1 or char in "\r\n":
            raise ValueError("insert_char expects one non-newline character")
        row = self._clamp_row(row)
        line = self.lines[row]
        self.lines[row] = line[:col] + char + line[col:]
        return row, col + 1

    def insert_string(self, row: int, col: int, text: str) -> Position:
        if text == "":
            return row, col
        row = self._clamp_row(row)
        normalized = normalize_newlines(text)
        parts = normalized.split("\n")
        if len(parts) == 1:
            line = self.lines[row]
            self.lines[row] = line[:col] + normalized + line[col:]
            return row, col + len(normalized)

        line = self.lines[row]
        before = line[:col]
        after = line[col:]
        replacement = [before + parts[0], *parts[1:-1], parts[-1] + after]
        self.lines[row : row + 1] = replacement
        return row + len(parts) - 1, len(parts[-1])

    def split_line(self, row: int, col: int) -> Position:
        row = self._clamp_row(row)
        line = self.lines[row]
        self.lines[row : row + 1] = [line[:col], line[col:]]
        return row + 1, 0

    def join_with_previous(self, row: int) -> Position:
        row = self._clamp_row(row)
        if row <= 0:
            return 0, 0
        previous_len = len(self.lines[row - 1])
        self.lines[row - 1] += self.lines[row]
        del self.lines[row]
        return row - 1, previous_len

    def delete_before(self, row: int, col: int) -> tuple[Position, str, Position] | None:
        row = self._clamp_row(row)
        if row == 0 and col == 0:
            return None
        if col > 0:
            line = self.lines[row]
            start = (row, col - 1)
            deleted = line[col - 1]
            self.lines[row] = line[: col - 1] + line[col:]
            return start, deleted, start

        start = (row - 1, len(self.lines[row - 1]))
        deleted = "\n"
        new_position = self.join_with_previous(row)
        return start, deleted, new_position

    def delete_at(self, row: int, col: int) -> tuple[Position, str, Position] | None:
        row = self._clamp_row(row)
        line = self.lines[row]
        if col < len(line):
            deleted = line[col]
            self.lines[row] = line[:col] + line[col + 1 :]
            return (row, col), deleted, (row, col)
        if row < self.line_count - 1:
            deleted = "\n"
            self.lines[row] += self.lines[row + 1]
            del self.lines[row + 1]
            return (row, col), deleted, (row, col)
        return None

    def delete_range(self, start: Position, end: Position) -> str:
        """Delete [start, end) and return the removed text."""

        start = self.clamp_position(*start)
        end = self.clamp_position(*end)
        if end < start:
            start, end = end, start
        start_row, start_col = start
        end_row, end_col = end
        if start == end:
            return ""

        if start_row == end_row:
            line = self.lines[start_row]
            removed = line[start_col:end_col]
            self.lines[start_row] = line[:start_col] + line[end_col:]
            return removed

        removed_parts = [self.lines[start_row][start_col:]]
        removed_parts.extend(self.lines[start_row + 1 : end_row])
        removed_parts.append(self.lines[end_row][:end_col])
        prefix = self.lines[start_row][:start_col]
        suffix = self.lines[end_row][end_col:]
        self.lines[start_row : end_row + 1] = [prefix + suffix]
        return "\n".join(removed_parts)

    def replace_line_range(self, start_row: int, end_row: int, new_lines: list[str]) -> None:
        if not new_lines:
            new_lines = [""]
        start_row = max(0, min(start_row, self.line_count))
        end_row = max(start_row, min(end_row, self.line_count))
        self.lines[start_row:end_row] = new_lines
        if not self.lines:
            self.lines = [""]

    def position_after_text(self, start: Position, text: str) -> Position:
        row, col = start
        normalized = normalize_newlines(text)
        parts = normalized.split("\n")
        if len(parts) == 1:
            return row, col + len(normalized)
        return row + len(parts) - 1, len(parts[-1])

    def visual_col(self, row: int, col: int, tab_width: int) -> int:
        row = self._clamp_row(row)
        visual = 0
        for char in self.lines[row][:col]:
            if char == "\t":
                visual += tab_width - (visual % tab_width)
            else:
                visual += char_display_width(char)
        return visual

    def logical_col_for_visual(self, row: int, target_visual: int, tab_width: int) -> int:
        """Return the logical column on row whose visual column is nearest target_visual.

        Used for sticky-column vertical movement so the cursor tracks the rendered
        column (tab-aware) rather than the raw character index. Ties prefer the
        smaller column. For tab-free lines this equals ``min(target_visual, len)``.
        """

        line = self.lines[self._clamp_row(row)]
        visual = 0
        best_col = 0
        best_distance = abs(visual - target_visual)
        for index, char in enumerate(line):
            if char == "\t":
                visual += tab_width - (visual % tab_width)
            else:
                visual += char_display_width(char)
            distance = abs(visual - target_visual)
            if distance < best_distance:
                best_distance = distance
                best_col = index + 1
        return best_col
