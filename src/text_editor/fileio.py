"""File open and atomic save helpers."""

from __future__ import annotations

import errno
import os
import shutil
import tempfile
from pathlib import Path

from .buffer import TextBuffer
from .config import EditorConfig
from .errors import FileOperationError


def _fsync_directory(directory: Path) -> None:
    """Best-effort fsync of a directory so a completed rename is durable.

    POSIX only; Windows cannot open a directory for fsync. Any failure is
    swallowed because the save itself has already succeeded by this point.
    """

    if not hasattr(os, "O_DIRECTORY"):
        return
    try:
        dir_fd = os.open(str(directory), os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        try:
            os.close(dir_fd)
        except OSError:
            pass


def _permission_denied_message() -> str:
    return "file is read-only or permission denied"


def _raise_read_oserror(path: Path, exc: OSError) -> None:
    if exc.errno in {errno.EACCES, errno.EPERM}:
        raise FileOperationError(_permission_denied_message()) from exc
    if exc.errno == errno.EISDIR:
        raise FileOperationError(f"not a regular file: {path}") from exc
    raise FileOperationError(f"could not read {path}: {exc}") from exc


def _raise_save_oserror(path: Path, exc: OSError) -> None:
    if exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
        raise FileOperationError(_permission_denied_message()) from exc
    raise FileOperationError(f"could not save {path}: {exc}") from exc


# The array-of-lines buffer loads the whole file into memory, so guard against
# opening something pathologically large (or a non-text blob) up front.
MAX_FILE_BYTES = 25 * 1024 * 1024


def read_text_file(path: Path) -> TextBuffer:
    if path.is_dir():
        raise FileOperationError(f"not a regular file: {path}")

    try:
        size = path.stat().st_size
    except FileNotFoundError as exc:
        raise FileOperationError(f"file not found: {path}") from exc
    except OSError as exc:
        _raise_read_oserror(path, exc)
    if size > MAX_FILE_BYTES:
        raise FileOperationError(f"file too large to open (> {MAX_FILE_BYTES // (1024 * 1024)} MB): {path}")

    try:
        # utf-8-sig transparently strips a leading byte-order mark (common on
        # Windows-authored files) while still reading BOM-less UTF-8 normally.
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise FileOperationError(f"file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise FileOperationError(f"could not decode as UTF-8: {path}") from exc
    except OSError as exc:
        _raise_read_oserror(path, exc)

    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise FileOperationError(f"file too large to open (> {MAX_FILE_BYTES // (1024 * 1024)} MB): {path}")

    return TextBuffer.from_text(text)


def effective_line_ending(buffer: TextBuffer, config: EditorConfig) -> str:
    if config.line_ending_policy == "lf":
        return "\n"
    if config.line_ending_policy == "crlf":
        return "\r\n"
    return buffer.line_ending


def text_for_save(buffer: TextBuffer, config: EditorConfig) -> tuple[str, str, bool, bool]:
    """Build save text without mutating the buffer.

    Returns ``(text, line_ending, line_ending_changed, added_trailing)``.
    """

    line_ending = effective_line_ending(buffer, config)
    line_ending_changed = line_ending != buffer.line_ending

    if buffer.lines == [""] and not buffer.trailing_newline:
        text = ""
    else:
        text = line_ending.join(buffer.lines)
        if buffer.trailing_newline:
            text += line_ending

    added_trailing = False
    if config.ensure_trailing_newline and text and not text.endswith(line_ending):
        text += line_ending
        added_trailing = True

    return text, line_ending, line_ending_changed, added_trailing


def _apply_default_mode(path: str) -> None:
    """Give a new file a sensible mode on POSIX (``666 & ~umask``)."""

    if not hasattr(os, "umask"):
        return
    current = os.umask(0)
    os.umask(current)
    os.chmod(path, 0o666 & ~current)


def write_text_file_atomic(path: Path, buffer: TextBuffer, config: EditorConfig) -> None:
    path = path.expanduser()
    # Write through a symlink to its real target rather than replacing the link,
    # and place the temp file in the target's own directory so os.replace stays
    # atomic (same filesystem).
    real = Path(os.path.realpath(path))
    parent = real.parent
    if not parent.exists():
        raise FileOperationError(f"directory does not exist: {parent}")

    text, line_ending, line_ending_changed, added_trailing = text_for_save(buffer, config)

    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{real.name}.", suffix=".tmp", dir=str(parent))
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # mkstemp creates the temp as 0600; carry the original file's permission
        # bits across the replace so saving does not strip them (e.g. the exec bit).
        if real.exists():
            shutil.copymode(real, temp_name)
        else:
            _apply_default_mode(temp_name)
        os.replace(temp_name, real)
        _fsync_directory(parent)
        if line_ending_changed:
            buffer.line_ending = line_ending
        if added_trailing:
            buffer.trailing_newline = True
    except OSError as exc:
        _raise_save_oserror(path, exc)
    finally:
        if temp_name is not None:
            try:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            except OSError:
                pass
