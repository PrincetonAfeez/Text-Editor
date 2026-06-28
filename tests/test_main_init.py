"""Tests for package entry points """

from __future__ import annotations

import importlib
import runpy

import pytest

from text_editor import __version__


def test_package_exports_version() -> None:
    assert __version__ == "0.1.0"


def test_main_module_invokes_app_main(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str] | None] = []

    def fake_main(argv=None):  # type: ignore[no-untyped-def]
        calls.append(list(argv) if argv is not None else None)
        return 0

    monkeypatch.setattr("text_editor.app.main", fake_main)
    import text_editor.__main__ as entry

    importlib.reload(entry)
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("text_editor.__main__", run_name="__main__")
    assert exc_info.value.code == 0
    assert calls == [None]
