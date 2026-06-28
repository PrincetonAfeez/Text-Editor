"""Additional command parser edge cases """

from __future__ import annotations

from text_editor.command_parser import parse_command


def test_parse_empty_parts_after_strip() -> None:
    request = parse_command(":   ")
    assert request.errors == ["empty command"]


def test_parse_shlex_failure() -> None:
    request = parse_command(':open "unterminated')
    assert request.errors
    assert "could not parse command" in request.errors[0]


def test_no_arg_command_with_arguments() -> None:
    request = parse_command(":write extra")
    assert request.errors == ["write does not take arguments"]


def test_find_without_query() -> None:
    request = parse_command(":find")
    assert request.errors == ["find requires search text"]


def test_goto_line_number_must_be_positive() -> None:
    request = parse_command(":goto 0")
    assert request.errors == ["goto line number must be at least 1"]


def test_set_requires_assignment_syntax() -> None:
    request = parse_command(":set tab_width")
    assert request.errors == ["invalid set assignment: tab_width"]


def test_aliases_cover_quit_variants() -> None:
    assert parse_command(":q").command == "quit"
    assert parse_command(":q!").command == "quit!"
