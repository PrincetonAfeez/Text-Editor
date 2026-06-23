from text_editor.command_parser import parse_command


def test_parse_aliases_and_quoted_arguments() -> None:
    request = parse_command(':saveas "notes with spaces.txt"')

    assert request.ok
    assert request.command == "saveas"
    assert request.args == ["notes with spaces.txt"]

    request = parse_command(":w")
    assert request.ok
    assert request.command == "write"


def test_parse_find_joins_unquoted_terms() -> None:
    request = parse_command(":find hello world")

    assert request.ok
    assert request.command == "find"
    assert request.args == ["hello world"]


def test_parser_reports_validation_errors() -> None:
    assert parse_command(":").errors == ["empty command"]
    assert parse_command(":nope").errors == ["unknown command: nope"]
    assert parse_command(":goto abc").errors == ["goto requires an integer line number"]
    assert parse_command(":open a b").errors == ["open got unexpected extra arguments"]
    assert parse_command(":set bad=true").errors == ["unknown config key: bad"]


def test_parse_set_assignments() -> None:
    request = parse_command(":set tab_width=2 expand_tabs=false")

    assert request.ok
    assert request.options == {"tab_width": "2", "expand_tabs": "false"}
