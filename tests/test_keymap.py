"""Tests for text_editor.keymap """

from text_editor.keymap import available_keymaps, default_keymap, keymap_for

def test_default_is_a_registered_keymap() -> None:
    assert "default" in available_keymaps()
    assert keymap_for("default") == default_keymap()


def test_keymap_for_binds_expected_commands() -> None:
    keymap = keymap_for("default")
    assert keymap["CTRL_S"] == "save"
    assert keymap["LEFT"] == "move_left"


def test_unknown_keymap_falls_back_to_default() -> None:
    assert keymap_for("does-not-exist") == default_keymap()
