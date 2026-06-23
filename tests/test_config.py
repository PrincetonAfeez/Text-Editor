from pathlib import Path

import pytest

from text_editor.config import EditorConfig, config_from_mapping, load_config, set_config_value


def test_config_validation_accepts_known_values() -> None:
    config, warnings = config_from_mapping(
        {
            "tab_width": 2,
            "expand_tabs": False,
            "line_ending_policy": "crlf",
            "search_case_sensitive": True,
        }
    )

    assert warnings == []
    assert config.tab_width == 2
    assert config.expand_tabs is False
    assert config.line_ending_policy == "crlf"
    assert config.search_case_sensitive is True


def test_config_validation_warns_and_falls_back() -> None:
    config, warnings = config_from_mapping({"tab_width": 99, "unknown": "x"})

    assert config == EditorConfig()
    assert "tab_width must be an integer from 1 to 16" in warnings
    assert "unknown config key: unknown" in warnings


def test_set_config_value_parses_string_booleans() -> None:
    config = set_config_value(EditorConfig(), "expand_tabs", "false")

    assert config.expand_tabs is False


def test_load_config_reads_editor_section(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[editor]\ntab_width = 2\nexpand_tabs = false\n", encoding="utf-8")

    config, warnings = load_config(path)

    assert warnings == []
    assert config.tab_width == 2
    assert config.expand_tabs is False


def test_load_config_reports_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("this is = not = valid", encoding="utf-8")

    config, warnings = load_config(path)

    assert config == EditorConfig()
    assert warnings and "invalid config TOML" in warnings[0]


def test_load_config_warns_when_explicit_path_is_missing(tmp_path: Path) -> None:
    config, warnings = load_config(tmp_path / "absent.toml")

    assert config == EditorConfig()
    assert warnings and "config not found" in warnings[0]


def test_tab_width_rejects_boolean() -> None:
    # bool is a subclass of int, so this must be rejected rather than become 1.
    config, warnings = config_from_mapping({"tab_width": True})

    assert config == EditorConfig()
    assert "tab_width must be an integer from 1 to 16" in warnings


def test_ensure_trailing_newline_parses_and_defaults_true() -> None:
    assert EditorConfig().ensure_trailing_newline is True

    config, warnings = config_from_mapping({"ensure_trailing_newline": False})

    assert warnings == []
    assert config.ensure_trailing_newline is False


def test_set_config_value_rejects_unknown_keymap() -> None:
    with pytest.raises(ValueError, match="unknown keymap"):
        set_config_value(EditorConfig(), "keymap_name", "vim")
