from text_editor.errors import EditorError, FileOperationError


def test_editor_error_exposes_message() -> None:
    exc = EditorError("hello")

    assert str(exc) == "hello"
    assert exc.message == "hello"


def test_file_operation_error_is_editor_error() -> None:
    exc = FileOperationError("could not save")

    assert isinstance(exc, EditorError)
    assert exc.message == "could not save"
