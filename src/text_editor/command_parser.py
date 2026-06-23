"""Small command-mode parser."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field

from .config import VALID_CONFIG_KEYS

ALIASES = {
    "w": "write",
    "q": "quit",
    "q!": "quit!",
}

NO_ARG_COMMANDS = {"write", "quit", "quit!", "wq", "next", "prev", "help"}
ONE_ARG_COMMANDS = {"open", "saveas", "goto"}
KNOWN_COMMANDS = NO_ARG_COMMANDS | ONE_ARG_COMMANDS | {"find", "set"}


@dataclass(frozen=True)
class CommandRequest:
    command: str | None
    args: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    raw: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.command is not None


def parse_command(raw: str) -> CommandRequest:
    original = raw
    raw = raw.strip()
    if raw.startswith(":"):
        raw = raw[1:].strip()
    if not raw:
        return CommandRequest(None, raw=original, errors=["empty command"])

    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return CommandRequest(None, raw=original, errors=[f"could not parse command: {exc}"])

    if not parts:
        return CommandRequest(None, raw=original, errors=["empty command"])

    command = ALIASES.get(parts[0], parts[0])
    args = parts[1:]
    errors: list[str] = []
    options: dict[str, str] = {}

    if command not in KNOWN_COMMANDS:
        return CommandRequest(command, args, raw=original, errors=[f"unknown command: {command}"])

    if command in NO_ARG_COMMANDS and args:
        errors.append(f"{command} does not take arguments")

    if command in ONE_ARG_COMMANDS:
        if not args:
            errors.append(f"{command} requires an argument")
        elif len(args) > 1:
            errors.append(f"{command} got unexpected extra arguments")

    if command == "goto" and len(args) == 1:
        try:
            line_number = int(args[0])
            if line_number < 1:
                errors.append("goto line number must be at least 1")
        except ValueError:
            errors.append("goto requires an integer line number")

    if command == "find":
        if not args:
            errors.append("find requires search text")
        else:
            args = [" ".join(args)]

    if command == "set":
        if not args:
            errors.append("set requires key=value")
        for assignment in args:
            if "=" not in assignment:
                errors.append(f"invalid set assignment: {assignment}")
                continue
            key, value = assignment.split("=", 1)
            if key not in VALID_CONFIG_KEYS:
                errors.append(f"unknown config key: {key}")
                continue
            options[key] = value

    return CommandRequest(command, args, options, original, errors)
