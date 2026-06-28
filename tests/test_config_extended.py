"""Additional config module coverage """

from __future__ import annotations

from pathlib import Path

import pytest

from text_editor.config import (
    EditorConfig,
    default_config_path,
    load_config,
    parse_bool,
    set_config_value,
)


def test_default_config_path_is_under_home() -> None:
    path = default_config_path()
    assert path.name == "config.toml"
    assert path.parent.name == "text-editor"


def test_load_config_oserror_on_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[editor]\ntab_width = 2\n", encoding="utf-8")
    original = Path.read_text

    def patched_read_text(self: Path, encoding: str = "utf-8") -> str:
        if self == path:
            raise OSError("permission denied")
        return original(self, encoding)

    monkeypatch.setattr(Path, "read_text", patched_read_text)
    config, warnings = load_config(path)
    assert config == EditorConfig()
    assert warnings and "could not read config" in warnings[0]


def test_load_config_rejects_non_table_editor_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[editor]\ntab_width = 2\n", encoding="utf-8")

    monkeypatch.setattr(
        "text_editor.config.tomllib.loads",
        lambda _text: {"editor": "not-a-table"},
    )
    config, warnings = load_config(path)
    assert config == EditorConfig()
    assert warnings == ["config [editor] section must be a table"]


def test_parse_bool_accepts_common_literals() -> None:
    assert parse_bool("yes") is True
    assert parse_bool("OFF") is False


def test_parse_bool_rejects_non_bool_int() -> None:
    with pytest.raises(ValueError, match="expected boolean"):
        parse_bool(1)


def test_parse_bool_rejects_unknown_string() -> None:
    with pytest.raises(ValueError, match="expected boolean"):
        parse_bool("maybe")


def test_set_config_value_all_keys() -> None:
    config = EditorConfig()
    config = set_config_value(config, "tab_width", 8)
    config = set_config_value(config, "expand_tabs", False)
    config = set_config_value(config, "line_ending_policy", "lf")
    config = set_config_value(config, "search_case_sensitive", True)
    config = set_config_value(config, "keymap_name", "default")
    config = set_config_value(config, "show_status_hints", False)
    config = set_config_value(config, "ensure_trailing_newline", False)
    assert config.tab_width == 8
    assert config.line_ending_policy == "lf"
    assert config.show_status_hints is False


def test_set_config_value_rejects_invalid_line_ending_policy() -> None:
    with pytest.raises(ValueError, match="line_ending_policy"):
        set_config_value(EditorConfig(), "line_ending_policy", "mac")


def test_set_config_value_rejects_empty_keymap_name() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        set_config_value(EditorConfig(), "keymap_name", "")


def test_set_config_value_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="unknown config key"):
        set_config_value(EditorConfig(), "not_a_key", "x")
