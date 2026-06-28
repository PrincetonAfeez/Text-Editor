"""User-facing exceptions for editor operations """

from __future__ import annotations


class EditorError(Exception):
    """An error that should be shown in the message bar."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FileOperationError(EditorError):
    """Raised when file open or save cannot be completed."""
