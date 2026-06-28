"""Data-driven key binding tables """

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyBinding:
    key: str
    command: str
    description: str


DEFAULT_BINDINGS: tuple[KeyBinding, ...] = (
    KeyBinding("CTRL_S", "save", "save"),
    KeyBinding("CTRL_Q", "quit", "quit"),
    KeyBinding("CTRL_F", "find_prompt", "find"),
    KeyBinding("CTRL_N", "find_next", "next search match"),
    KeyBinding("CTRL_B", "find_previous", "previous search match"),
    KeyBinding("CTRL_P", "command_prompt", "command mode"),
    KeyBinding("CTRL_G", "help", "help"),
    KeyBinding("CTRL_Z", "undo", "undo"),
    KeyBinding("CTRL_Y", "redo", "redo"),
    KeyBinding("LEFT", "move_left", "move left"),
    KeyBinding("RIGHT", "move_right", "move right"),
    KeyBinding("UP", "move_up", "move up"),
    KeyBinding("DOWN", "move_down", "move down"),
    KeyBinding("HOME", "move_home", "line start"),
    KeyBinding("END", "move_end", "line end"),
    KeyBinding("PAGE_UP", "page_up", "page up"),
    KeyBinding("PAGE_DOWN", "page_down", "page down"),
    KeyBinding("ENTER", "insert_newline", "insert newline"),
    KeyBinding("BACKSPACE", "backspace", "delete before cursor"),
    KeyBinding("DELETE", "delete_forward", "delete at cursor"),
    KeyBinding("TAB", "insert_tab", "insert tab"),
)


KEYMAPS: dict[str, tuple[KeyBinding, ...]] = {
    "default": DEFAULT_BINDINGS,
}


def available_keymaps() -> frozenset[str]:
    return frozenset(KEYMAPS)


def keymap_for(name: str) -> dict[str, str]:
    """Return the binding table for a named keymap, falling back to default."""

    bindings = KEYMAPS.get(name, DEFAULT_BINDINGS)
    return {binding.key: binding.command for binding in bindings}


def default_keymap() -> dict[str, str]:
    return keymap_for("default")
