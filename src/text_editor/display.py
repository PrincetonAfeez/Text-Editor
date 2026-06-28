"""Display-width helpers for tab- and wide-character-aware rendering 

These functions are curses-free so the rendering math can be unit-tested without
a terminal. East Asian wide/fullwidth characters occupy two columns; everything
else occupies one. Zero-width combining marks and full grapheme clusters are out
of scope (a documented limitation), so a base letter plus a combining mark is
treated as two single-width cells.
"""

from __future__ import annotations

import unicodedata

CONTROL_PLACEHOLDER = "�"


def char_display_width(char: str) -> int:
    """Return the number of terminal columns a single character occupies."""

    if unicodedata.east_asian_width(char) in ("W", "F"):
        return 2
    return 1


def is_control(char: str) -> bool:
    """True for C0/C1 control characters (which can corrupt the terminal)."""

    code = ord(char)
    return code < 0x20 or 0x7F <= code <= 0x9F


def sanitize_controls(text: str) -> str:
    """Replace C0/C1 control characters with a visible placeholder."""

    if not any(is_control(ch) for ch in text):
        return text
    return "".join(CONTROL_PLACEHOLDER if is_control(ch) else ch for ch in text)


def visible_segment(line: str, start_col: int, width: int, tab_width: int) -> str:
    """Render the slice of ``line`` spanning display columns [start_col, start_col+width).

    Tabs expand to the configured stop, control characters become a placeholder,
    and East Asian wide characters occupy two columns. A wide character that
    straddles either edge of the window is shown as spaces on its visible side.
    The result is padded with spaces to exactly ``width`` columns.
    """

    if width <= 0:
        return ""
    end_col = start_col + width
    out: list[str] = []
    produced = 0
    col = 0
    for ch in line:
        if col >= end_col:
            break
        if ch == "\t":
            stop = tab_width - (col % tab_width)
            for _ in range(stop):
                if start_col <= col < end_col:
                    out.append(" ")
                    produced += 1
                col += 1
            continue
        if is_control(ch):
            disp, w = CONTROL_PLACEHOLDER, 1
        else:
            w = char_display_width(ch)
            disp = ch
        cell_end = col + w
        if cell_end <= start_col:  # entirely left of the window
            col = cell_end
            continue
        if col < start_col:  # left edge cuts through a wide character
            half = cell_end - start_col
            out.append(" " * half)
            produced += half
            col = cell_end
            continue
        if cell_end > end_col:  # right edge cuts through a wide character
            half = end_col - col
            out.append(" " * half)
            produced += half
            col = cell_end
            break
        out.append(disp)
        produced += w
        col = cell_end
    if produced < width:
        out.append(" " * (width - produced))
    return "".join(out)


def visual_length(text: str, tab_width: int = 8) -> int:
    """Return the number of display columns occupied by ``text``."""

    visual = 0
    for char in text:
        if char == "\t":
            visual += tab_width - (visual % tab_width)
        elif is_control(char):
            visual += 1
        else:
            visual += char_display_width(char)
    return visual
