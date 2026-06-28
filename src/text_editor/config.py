"""Configuration loading and validation """

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .keymap import available_keymaps

VALID_LINE_ENDING_POLICIES = {"preserve", "lf", "crlf"}
VALID_CONFIG_KEYS = {
    "tab_width",
    "expand_tabs",
    "line_ending_policy",
    "search_case_sensitive",
    "keymap_name",
    "show_status_hints",
    "ensure_trailing_newline",
}


@dataclass(frozen=True)
class EditorConfig:
    tab_width: int = 4
    expand_tabs: bool = True
    line_ending_policy: str = "preserve"
    search_case_sensitive: bool = False
    keymap_name: str = "default"
    show_status_hints: bool = True
    ensure_trailing_newline: bool = True


def default_config_path() -> Path:
    return Path.home() / ".config" / "text-editor" / "config.toml"


def load_config(path: Path | None = None) -> tuple[EditorConfig, list[str]]:
    config_path = path or default_config_path()
    if not config_path.exists():
        if path is not None:
            # An explicitly requested config that is missing is worth reporting;
            # a missing default location is normal and stays silent.
            return EditorConfig(), [f"config not found: {config_path}"]
        return EditorConfig(), []
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return EditorConfig(), [f"could not read config: {exc}"]
    except tomllib.TOMLDecodeError as exc:
        return EditorConfig(), [f"invalid config TOML: {exc}"]

    section = raw.get("editor", raw)
    if not isinstance(section, dict):
        return EditorConfig(), ["config [editor] section must be a table"]
    return config_from_mapping(section)


def config_from_mapping(values: dict[str, Any]) -> tuple[EditorConfig, list[str]]:
    config = EditorConfig()
    warnings: list[str] = []
    for key, value in values.items():
        if key not in VALID_CONFIG_KEYS:
            warnings.append(f"unknown config key: {key}")
            continue
        try:
            config = set_config_value(config, key, value)
        except ValueError as exc:
            warnings.append(str(exc))
    return config, warnings


def set_config_value(config: EditorConfig, key: str, value: Any) -> EditorConfig:
    if key not in VALID_CONFIG_KEYS:
        raise ValueError(f"unknown config key: {key}")

    if key == "tab_width":
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError as exc:
                raise ValueError("tab_width must be an integer") from exc
        # bool is a subclass of int, so reject it explicitly (`tab_width = true`).
        if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 16:
            raise ValueError("tab_width must be an integer from 1 to 16")
        return replace(config, tab_width=value)

    if key == "expand_tabs":
        return replace(config, expand_tabs=parse_bool(value))

    if key == "search_case_sensitive":
        return replace(config, search_case_sensitive=parse_bool(value))

    if key == "show_status_hints":
        return replace(config, show_status_hints=parse_bool(value))

    if key == "ensure_trailing_newline":
        return replace(config, ensure_trailing_newline=parse_bool(value))

    if key == "line_ending_policy":
        if value not in VALID_LINE_ENDING_POLICIES:
            raise ValueError("line_ending_policy must be preserve, lf, or crlf")
        return replace(config, line_ending_policy=str(value))

    if key == "keymap_name":
        if not isinstance(value, str) or not value:
            raise ValueError("keymap_name must be a non-empty string")
        if value not in available_keymaps():
            names = ", ".join(sorted(available_keymaps()))
            raise ValueError(f"unknown keymap: {value}; available: {names}")
        return replace(config, keymap_name=value)

    raise ValueError(f"unknown config key: {key}")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    raise ValueError(f"expected boolean value, got {value!r}")
