""" Shared fakes for headless curses tests """

from __future__ import annotations

import curses


class FakeScreen:
    """Records draws and feeds queued keys to ``get_wch``."""

    def __init__(self, height: int, width: int, keys: list[object] | None = None) -> None:
        self.height = height
        self.width = width
        self.cells = [[" "] * width for _ in range(height)]
        self.attrs = [[0] * width for _ in range(height)]
        self.cursor = (0, 0)
        self._keys = list(keys or [])

    def getmaxyx(self) -> tuple[int, int]:
        return (self.height, self.width)

    def erase(self) -> None:
        self.cells = [[" "] * self.width for _ in range(self.height)]
        self.attrs = [[0] * self.width for _ in range(self.height)]

    def addstr(self, row: int, col: int, text: str, attr: int = 0) -> None:
        if row < 0 or row >= self.height or col < 0:
            raise curses.error("addstr out of bounds")
        for offset, char in enumerate(text):
            column = col + offset
            if column >= self.width:
                raise curses.error("addstr past right edge")
            self.cells[row][column] = char
            self.attrs[row][column] = attr

    def move(self, y: int, x: int) -> None:
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            raise curses.error("move out of bounds")
        self.cursor = (y, x)

    def noutrefresh(self) -> None:
        pass

    def refresh(self) -> None:
        pass

    def keypad(self, _enabled: bool) -> None:
        pass

    def get_wch(self) -> object:
        if not self._keys:
            raise curses.error("no input")
        item = self._keys.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def row_text(self, row: int) -> str:
        return "".join(self.cells[row])
