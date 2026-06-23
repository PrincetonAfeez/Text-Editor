"""Shared test harness.

``text_editor.render`` imports ``curses`` at module load, which is unavailable on
machines without it (and a real curses needs a live terminal). Installing a
deterministic fake here lets the render and key-dispatch tests run anywhere, and
behave identically whether or not a real curses happens to be installed. No test
in this suite needs the real library.
"""

import sys
import types

_fake_curses = types.ModuleType("curses")
_fake_curses.error = type("error", (Exception,), {})  # type: ignore[attr-defined]
_fake_curses.A_REVERSE = 1 << 18  # type: ignore[attr-defined]
_fake_curses.doupdate = lambda: None  # type: ignore[attr-defined]
_fake_curses.KEY_ENTER = 343  # type: ignore[attr-defined]
_fake_curses.KEY_BACKSPACE = 263  # type: ignore[attr-defined]
_fake_curses.KEY_LEFT = 260  # type: ignore[attr-defined]
_fake_curses.KEY_RIGHT = 261  # type: ignore[attr-defined]
_fake_curses.KEY_UP = 259  # type: ignore[attr-defined]
_fake_curses.KEY_DOWN = 258  # type: ignore[attr-defined]
_fake_curses.KEY_HOME = 262  # type: ignore[attr-defined]
_fake_curses.KEY_END = 360  # type: ignore[attr-defined]
_fake_curses.KEY_PPAGE = 339  # type: ignore[attr-defined]
_fake_curses.KEY_NPAGE = 338  # type: ignore[attr-defined]
_fake_curses.KEY_DC = 330  # type: ignore[attr-defined]
_fake_curses.KEY_RESIZE = 410  # type: ignore[attr-defined]

sys.modules["curses"] = _fake_curses
