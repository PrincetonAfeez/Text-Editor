# Architecture Decision Record
## App — Text Editor
**Terminal Editing Systems Group | Document 1 of 5**
**Status: Accepted**

---

## Context

Terminal Text Editor is a curses-based CLI text editor built as a systems programming capstone. The project is intentionally terminal-only: no Django, Flask, HTMX, database, or web dashboard. The learning goal is direct control of the terminal boundary: screen redraws, cursor placement, key decoding, command dispatch, file I/O, search, configuration, undo/redo, and dirty-buffer safety.

The PyPI package name is `terminal-text-editor`, the importable module is `text_editor`, and the console command is `text-editor`. The runtime target is Python 3.11+, with `windows-curses` as a Windows-only runtime dependency.

---

## Decisions

### Decision 1 — Keep the project terminal-only

**Chosen:** Build a curses-based CLI editor launched with `text-editor`.

**Rejected:** A GUI, web dashboard, Django/Flask app, HTMX front end, or IDE-style interface.

**Reason:** The capstone is about terminal mechanics, not web or GUI frameworks. A curses editor forces the project to own key decoding, raw mode, status bars, rendering, viewport movement, and terminal cleanup.

---

### Decision 2 — Isolate curses from core logic

**Chosen:** Keep buffer, cursor, viewport, command parsing, file I/O, undo, search, and config in curses-free modules.

**Rejected:** Put all editor logic inside the curses loop.

**Reason:** Core behavior can be unit-tested without a real terminal. Rendering and input become adapters around a testable state model.

---

### Decision 3 — Use an array-of-lines buffer

**Chosen:** Store text as `list[str]`.

**Rejected:** Gap buffer, piece table, rope, memory-mapped file, or streaming document model.

**Reason:** An array of lines is honest, simple, and sufficient for ordinary files. The project documents that this is not ideal for huge files or very long lines.

---

### Decision 4 — Read UTF-8 and cap file size

**Chosen:** Read files with UTF-8/UTF-8 BOM handling and reject files over 25 MB.

**Rejected:** Encoding detection and unlimited loading.

**Reason:** The editor stores the whole buffer in memory. UTF-8-only behavior and a clear size cap keep scope practical and error handling predictable.

---

### Decision 5 — Save atomically

**Chosen:** Write to a temporary file in the target directory, flush, fsync, copy permissions, replace with `os.replace`, and fsync the directory on POSIX.

**Rejected:** Direct overwrite.

**Reason:** Atomic save avoids leaving a partially overwritten user file if a write fails.

---

### Decision 6 — Preserve line endings by default

**Chosen:** Detect the first line-ending style and preserve it unless config asks for LF or CRLF.

**Rejected:** Always normalize to LF on save.

**Reason:** A text editor should avoid unnecessary file churn.

---

### Decision 7 — Use reversible edit objects for undo/redo

**Chosen:** Store `InsertEdit` and `DeleteEdit` objects with undo/redo methods.

**Rejected:** Store whole-buffer snapshots for every edit.

**Reason:** Reversible edits teach state transitions and use less memory for normal editing.

---

### Decision 8 — Merge continuous typing into one undo group

**Chosen:** Continuous printable typing merges into one undo step; cursor movement, newline, and delete break groups.

**Rejected:** One undo step per character.

**Reason:** Usable undo should remove a typed run, not only the last character.

---

### Decision 9 — Use a structured command-mode parser

**Chosen:** Parse command strings into `CommandRequest` objects using `shlex`.

**Rejected:** Dispatch raw command strings directly.

**Reason:** Validation becomes explicit, testable, and independent of curses.

---

### Decision 10 — Use a data-driven keymap

**Chosen:** Map decoded key names to command names through a keymap registry.

**Rejected:** Hard-code every key in the app loop.

**Reason:** The default key bindings are visible and future keymaps can be added without changing core command functions.

---

### Decision 11 — Sanitize control characters during rendering

**Chosen:** Replace C0/C1 control characters with a visible placeholder and account for East Asian wide/fullwidth characters.

**Rejected:** Printing file text directly to the terminal.

**Reason:** Untrusted file content must not inject terminal control sequences.

---

## Consequences

**Positive:**
- Core editor behavior is highly testable.
- Curses-specific code is thin.
- Atomic save protects user files.
- Dirty state can clear after undo returns to saved content.
- Command mode and key bindings are explicit.
- The implementation is proportional to a capstone.

**Trade-offs:**
- Whole-file, array-of-lines storage is not ideal for huge files.
- UTF-8 is the only encoding.
- There is no mouse support, syntax highlighting, plugins, LSP, split panes, or collaboration.
- Unicode grapheme clusters are not fully modeled.
- Only the default keymap is registered today.

---

## Alternatives Not Explored

Gap buffer, piece table, rope, memory-mapped editing, syntax highlighting, mouse support, plugins, language-server integration, split panes, tabs, multi-file project indexing, collaborative editing, encryption, full Unicode grapheme-cluster editing, or a web/GUI surface.

---

*Constitution reference: Article 1, Article 3.3, Article 4, Article 5, Article 6, and Article 7.*

---


# Technical Design Document
## App — Text Editor
**Terminal Editing Systems Group | Document 2 of 5**

---

## Overview

Terminal Text Editor is a Python curses editor with a curses-free editing core. It supports opening UTF-8 files, editing an array-of-lines buffer, cursor movement, tab-aware viewport math, command mode, search, undo/redo, runtime configuration, safe file saves, and a minimal curses UI.

**Package:** `terminal-text-editor`  
**Import module:** `text_editor`  
**Console script:** `text-editor`  
**Python:** `>=3.11`  
**Runtime dependency:** `windows-curses` only on Windows  
**Coverage gate:** 98%

---

## System Context

```text
Terminal
  │
  ▼
text-editor CLI
  │
  ▼
create_initial_state()
  ├── parse argv
  ├── load config
  ├── open optional file
  └── build EditorState
        │
        ▼
curses.wrapper()
  │
  ▼
CursesApp.run()
  ├── raw mode
  ├── draw frame
  ├── get key
  ├── decode key
  ├── dispatch keymap command
  ├── prompt for search/command/save-as
  └── mutate EditorState
```

---

## Main Modules

```text
buffer.py          array-of-lines text model and edit primitives
cursor.py          pure cursor movement and sticky-column rules
viewport.py        viewport offset math
state.py           EditorState, modes, dirty tracking
undo.py            reversible edit history
search.py          match finding and navigation
fileio.py          UTF-8 open and atomic save
config.py          TOML config and validation
command_parser.py  command-mode parser
commands.py        named editor commands
keymap.py          key binding registry
display.py         tab/wide/control-character display math
render.py          thin curses renderer
app.py             curses setup, key decoding, app loop, CLI entry point
```

---

## Core Data Structures

### `TextBuffer`

Stores:
- `lines: list[str]`
- `line_ending: str`
- `trailing_newline: bool`

Responsibilities:
- detect and preserve line endings
- normalize newlines internally
- insert characters and strings
- split and join lines
- delete before/at/ranges
- convert logical columns to visual columns for tabs/wide chars
- convert buffer back to text for save/dirty comparison

---

### `Cursor`

Stores:
- `row`
- `col`
- `sticky_col`

Movement functions are pure:
- left/right wrap across line boundaries
- up/down preserve a visual sticky column
- home/end move within line
- page up/down move by visible page size

---

### `Viewport`

Stores:
- `row_offset`
- `col_offset`

`ensure_visible()` adjusts offsets so the cursor remains inside the visible frame.

---

### `EditorConfig`

Defaults:
- `tab_width = 4`
- `expand_tabs = true`
- `line_ending_policy = "preserve"`
- `search_case_sensitive = false`
- `keymap_name = "default"`
- `show_status_hints = true`
- `ensure_trailing_newline = true`

Validation rejects unknown keys, invalid line-ending policy, invalid keymap, non-bool booleans, and tab widths outside 1–16.

---

### `EditorState`

Tracks:
- buffer
- config
- current path
- cursor
- viewport
- screen size
- dirty flag
- saved text
- status message
- quit warning
- interaction mode
- prompt text
- undo history
- search state

Dirty state is recomputed by comparing `buffer.to_text()` to `saved_text`.

---

### `UndoHistory`

Contains:
- undo stack
- redo stack
- maximum 1000 entries
- merge-block flag

Edits:
- `InsertEdit`
- `DeleteEdit`

Typing edits can merge when adjacent and marked as `typing`.

---

### `SearchState`

Contains:
- query
- match list
- current index
- case-sensitivity flag

Search matches are line/column/length tuples. Next/previous navigation wraps.

---

## Command Mode

The command parser returns:

```python
CommandRequest(
    command: str | None,
    args: list[str],
    options: dict[str, str],
    raw: str,
    errors: list[str],
)
```

Supported commands:
- `open`
- `write` / `w`
- `saveas`
- `quit` / `q`
- `quit!` / `q!`
- `wq`
- `find`
- `next`
- `prev`
- `goto`
- `set`
- `help`

`shlex.split()` supports quoted paths and search text.

---

## Key Dispatch

`CursesApp.decode_key()` normalizes:
- curses integer keys to symbolic names
- Enter/Tab/Backspace/Delete
- Ctrl-A through Ctrl-Z to `CTRL_X`
- printable characters as themselves

`handle_key()` routes:
- printable characters to insertion
- Ctrl-F to search prompt
- Ctrl-P to command prompt
- Ctrl-S to save or save-as prompt
- registered keymap commands to `KEY_COMMANDS`

---

## File I/O

### Read

`read_text_file()`:
- rejects directories
- checks size before reading
- reads `utf-8-sig`
- rejects files over 25 MB
- converts to `TextBuffer`

### Save

`write_text_file_atomic()`:
- resolves symlink target
- writes temp file in same directory
- flushes and fsyncs
- copies original permissions or applies default mode
- replaces with `os.replace`
- fsyncs directory on POSIX
- updates buffer line ending/trailing newline metadata when save policy changes output

---

## Rendering

`CursesRenderer.draw()`:
- resizes editor state from terminal dimensions
- erases screen
- draws visible buffer rows only
- draws reverse-video status bar
- draws message or prompt bar
- highlights current search match when visible
- places cursor based on visual column
- uses `noutrefresh()` and `doupdate()`

Display helpers:
- expand tabs
- replace control chars with placeholder
- handle East Asian wide/fullwidth chars as two columns
- pad visible rows to width

---

## Error Handling

Handled errors show in the message bar:
- config warnings
- command parse errors
- file read/save errors
- search misses
- dirty quit warning

Process-level errors:
- missing curses prints to stderr and exits `1`
- argparse usage returns `2`

---

## Known Limits

No mouse support, syntax highlighting, LSP, plugins, split panes, full grapheme clusters, multi-file project model, collaboration, encryption, or large-file editing beyond 25 MB.

---

## Verification Summary

The project uses pytest, coverage, ruff, and strict mypy. CI runs on Ubuntu and Windows for Python 3.11 and 3.12, then runs Ruff, mypy, and pytest with coverage fail-under 98.

---

*Constitution reference: Article 4, Article 6, Article 7, and Article 8.*

---


# Interface Design Specification
## App — Text Editor
**Terminal Editing Systems Group | Document 3 of 5**

---

## Public CLI

```powershell
text-editor
text-editor notes.txt
python -m text_editor notes.txt
text-editor --config config.toml notes.txt
text-editor --version
```

---

## CLI Arguments

| Argument | Description |
|---|---|
| `file` | Optional file to open |
| `--config PATH` | TOML config file path |
| `--version` | Print version |

---

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Normal exit |
| `1` | Curses unavailable |
| `2` | Usage error from invalid CLI arguments |

---

## Default Keys

| Key | Action |
|---|---|
| Arrow keys | Move cursor |
| Home / End | Start/end of line |
| PageUp / PageDown | Move one visible page |
| Enter | Split line |
| Backspace | Delete before cursor |
| Delete | Delete at cursor |
| Tab | Insert tab or spaces |
| Ctrl-S | Save |
| Ctrl-Q | Quit with dirty warning |
| Ctrl-F | Search |
| Ctrl-N / Ctrl-B | Next / previous match |
| Ctrl-P | Command mode |
| Ctrl-Z / Ctrl-Y | Undo / redo |
| Ctrl-G | Help |

---

## Command Mode

Open with `Ctrl-P`.

Commands:

```text
:open path/to/file.txt
:write
:w
:saveas path/to/new-file.txt
:quit
:q
:quit!
:wq
:find text
:next
:prev
:goto 120
:set tab_width=4
:set expand_tabs=true
:help
```

Rules:
- quoted arguments accepted through `shlex`
- `:quit!` discards unsaved changes
- `:wq` saves when possible and quits
- `:set` accepts only known config keys
- invalid commands appear in message bar

---

## Config

Default file:

```text
~/.config/text-editor/config.toml
```

Example:

```toml
[editor]
tab_width = 4
expand_tabs = true
line_ending_policy = "preserve"
search_case_sensitive = false
keymap_name = "default"
show_status_hints = true
ensure_trailing_newline = true
```

Valid line-ending policies:
- `preserve`
- `lf`
- `crlf`

---

## File Behavior

Open:
- UTF-8 / UTF-8 with BOM
- reject directories
- reject files larger than 25 MB
- reject non-UTF-8
- preserve first detected line ending

Save:
- atomic temp-file replace
- preserve permissions
- write through symlinks
- fsync file and directory when possible
- optional final newline enforcement
- configurable line-ending policy

---

## Search

Search can be started with:
- `Ctrl-F`
- `:find text`

Behavior:
- incremental for Ctrl-F
- current match highlighted
- cancel returns to original cursor
- next/previous wrap
- case sensitivity follows config

---

## Undo/Redo

Keys:
- `Ctrl-Z`
- `Ctrl-Y`

Behavior:
- reversible edits
- continuous typing merges
- redo clears after new edit
- history capped at 1000 entries
- dirty state recomputed after undo/redo

---

## Public Python API

Common testable imports:

```python
from text_editor.buffer import TextBuffer
from text_editor.cursor import Cursor, move_left, move_right, move_up, move_down
from text_editor.viewport import Viewport, ensure_visible
from text_editor.command_parser import parse_command, CommandRequest
from text_editor.config import EditorConfig, load_config
from text_editor.fileio import read_text_file, write_text_file_atomic
from text_editor.state import EditorState
from text_editor.search import find_matches, move_match
from text_editor.undo import UndoHistory, InsertEdit, DeleteEdit
```

---

## Side Effects

| Operation | Side Effect |
|---|---|
| startup with file | Reads file |
| startup with config | Reads TOML |
| edit | Mutates buffer and dirty state |
| save | Writes and atomically replaces file |
| search | Moves cursor and search state |
| undo/redo | Mutates buffer/cursor |
| raw curses mode | Temporarily changes terminal mode |
| command `:open` | Replaces current buffer when clean |

---

*Constitution reference: Article 4, Article 6, and Article 8.*

---


# Runbook
## App — Text Editor
**Terminal Editing Systems Group | Document 4 of 5**

---

## Requirements

Runtime:
- Python 3.11+
- real terminal
- curses on Unix/macOS
- windows-curses on Windows

Development:
- pytest
- pytest-cov
- mypy
- ruff
- pip-tools

---

## Install

Editable dev install:

```powershell
python -m pip install -e ".[dev]"
```

Pinned dev install:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
```

Runtime-only install:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

---

## Run

```powershell
text-editor
text-editor notes.txt
python -m text_editor notes.txt
```

Use a real terminal rather than an IDE embedded console.

---

## Smoke Test

1. Run `text-editor`.
2. Type `hello`.
3. Press `Ctrl-S`.
4. Enter a save path when prompted.
5. Press `Ctrl-Q`.

Expected:
- text appears
- file saves
- editor exits normally

---

## Command Mode Demo

Press `Ctrl-P`, then run:

```text
:find hello
:goto 1
:set tab_width=2
:write
:quit
```

---

## Search Demo

Press `Ctrl-F`, type a term, then:
- `Ctrl-N` for next match
- `Ctrl-B` for previous match
- `Esc` to cancel

---

## Undo/Redo Demo

Type text, then:
- `Ctrl-Z` to undo
- `Ctrl-Y` to redo

Continuous typing should undo as one group.

---

## Config Demo

Create:

```toml
[editor]
tab_width = 2
expand_tabs = true
line_ending_policy = "lf"
search_case_sensitive = false
show_status_hints = true
ensure_trailing_newline = true
```

Run:

```powershell
text-editor --config config.toml notes.txt
```

---

## Quality Checks

```powershell
python -m pytest
python -m pytest -q --cov=text_editor --cov-report=term-missing --cov-fail-under=98
python -m ruff check src tests
python -m mypy
```

---

## CI Parity

CI runs:
- Ubuntu latest
- Windows latest
- Python 3.11 and 3.12
- editable dev install
- Ruff
- mypy
- pytest with coverage fail-under 98

---

## Troubleshooting

### Curses unavailable

Install the Windows curses dependency or run in a terminal with curses support.

```powershell
python -m pip install windows-curses
```

### Terminal behavior is broken after a crash

Run:

```bash
reset
```

or close and reopen the terminal.

### Ctrl-S / Ctrl-Q not received

Use a real terminal. Some IDE consoles intercept control keys.

### File too large

Files over 25 MB are intentionally rejected.

### Save fails

Check target path, parent directory, permissions, and read-only filesystem status.

### Non-UTF-8 file fails

Convert the file to UTF-8 before opening.

---

## Maintenance Notes

- Keep curses isolated from the editing core.
- Preserve atomic save behavior.
- Add tests before changing dirty-state logic.
- Add tests before changing key decoding.
- Add tests before changing command parser validation.
- Keep terminal-only scope clear.
- Do not claim huge-file support without replacing the buffer model.
- Preserve the 98% coverage gate unless scope meaningfully changes.

---

*Constitution reference: Article 6, Article 5, and Article 8.*

---


# Lessons Learned
## App — Text Editor
**Terminal Editing Systems Group | Document 5 of 5**

---

## Why This Design Was Chosen

A terminal editor is a strong systems capstone because it requires direct control of a real terminal while still needing a careful internal model. The design separates the parts that are easy to test from the parts that depend on curses.

The array-of-lines buffer was chosen because it makes edits understandable. It is not the most scalable editor data structure, but it is the right size for a capstone that also needs command mode, search, undo, rendering, configuration, and atomic save behavior.

The atomic save path is one of the most important production-minded decisions. A text editor should not corrupt a user file just because a write fails midway.

---

## What Was Intentionally Omitted

- Vim/Emacs compatibility
- mouse support
- syntax highlighting
- language-server protocol
- plugin system
- split panes
- collaborative editing
- huge-file editing
- non-UTF-8 encodings
- full Unicode grapheme clusters
- encryption

---

## Biggest Weakness

The biggest weakness is the buffer model. `list[str]` is simple and testable, but it is not optimal for huge files or heavy mid-file editing. A piece table or gap buffer would be the next major architectural upgrade.

The second weakness is Unicode handling. Wide characters and control characters are handled, but grapheme clusters, combining marks, and zero-width characters are not modeled like a mature editor would.

The third weakness is minimal UI scope. It edits text well enough for the capstone, but it is not an IDE.

---

## Scaling Considerations

For larger files:
- replace the buffer with a piece table or gap buffer
- make search incremental
- avoid full-buffer dirty comparison
- add viewport-aware loading

For richer terminal UX:
- add syntax highlighting
- add line numbers
- add selection
- add configurable keymaps
- add command history

For Unicode:
- add grapheme segmentation
- test combining marks and zero-width behavior
- document terminal-specific differences

---

## Next Refactor

1. Introduce a piece table buffer.
2. Replace command dispatch branches with a command registry.
3. Load user-defined keymaps from TOML.
4. Make large-file search incremental.
5. Add grapheme-cluster-aware cursor movement.

---

## What This Project Taught

- Terminal apps are systems software.
- Curses should be an adapter, not the whole architecture.
- Buffer choice shapes every editing operation.
- Undo/redo needs explicit reversible state.
- Dirty state should be content-based.
- Atomic save behavior matters.
- Rendering must sanitize untrusted text.
- Clear scope makes the project stronger.

---

*Constitution v2.0 checklist: This document satisfies Article 5, Article 6, and Article 7 for Text Editor.*
