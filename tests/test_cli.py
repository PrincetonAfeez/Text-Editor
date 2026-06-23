import pytest

from text_editor import __version__
from text_editor.app import build_arg_parser, main


def test_version_flag_prints_version_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_arg_parser().parse_args(["--version"])

    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_main_returns_2_for_invalid_arguments() -> None:
    assert main(["--not-a-real-flag"]) == 2


def test_main_returns_0_for_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out
