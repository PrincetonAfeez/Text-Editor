# ADR 0001: Core Architecture Decisions
 
## Status

Accepted.

## Decisions

### 1. CLI-only application

The editor is a terminal application because the capstone goal is direct systems
work at the terminal boundary: screen control, input decoding, rendering,
buffers, file I/O, and undo history.

### 2. Use curses

Curses is the standard Python-facing terminal screen library on Unix-like
systems and is available on Windows through `windows-curses`. It provides raw
screen drawing, key codes, cursor control, and resize events without adding a web
or GUI framework.

### 3. No Django, HTMX, or web layer

A web layer would move the project away from the terminal systems problem and
into routing, templates, HTTP, and browser state. Those are useful topics, but
they are not the point of this editor.

### 4. Separate buffer, view, input, render, file I/O, and undo

The editor keeps pure logic separate from the curses adapter. This makes the
core behavior testable without a terminal and prevents the application from
becoming one large keypress loop.

### 5. Array-of-lines buffer

The first buffer representation is `list[str]`. It is clear, idiomatic, and
sufficient for ordinary files. The tradeoff is that very large files and very
large single lines may require more copying than a gap buffer or piece table.

### 6. Data-driven key bindings

Key bindings are represented as data in `keymap.py`, mapping decoded key names
to named commands. This keeps input decoding separate from editor behavior.

### 7. Command mode parser

Command mode uses a parser that returns a structured request. This gives the
project a real parsing boundary and allows command validation to be tested
without curses.

### 8. Command-pattern undo/redo

Undo history stores reversible edit command objects. Each edit can undo and redo
itself, and the history manages stack movement and redo invalidation.

### 9. Typed character grouping

Continuous printable typing is grouped into one undo step. Cursor movement,
newlines, and deletions break the group. This matches user expectations better
than one undo step per character.

### 10. Atomic save

Saves write to a temporary file in the target directory, flush and fsync it, then
replace the destination. This protects against partial overwrites better than
writing directly to the original file.

### 11. Config loading is core

An explicit `EditorConfig` object gives startup behavior and command-mode
settings a single validated source of truth. Invalid config entries warn and
fall back to defaults.

### 12. Encryption is not central

The editor focuses on file integrity and ordinary save safety. Encryption would
require a different threat model and careful security claims that are outside
this capstone.

### 13. Recovery journal is not included in core

The core implementation includes atomic save and graceful error handling. A
future recovery journal could be added later, but it is not required for the
first complete version.
