# CORE Requirements

This document summarizes the **CORE** scope for the terminal text editor capstone.
Stretch goals (word motion, selection, regex search, recovery journal, and similar)
are intentionally deferred.

## Editor shell

- Curses-based terminal UI with a main input loop
- Raw terminal mode so control keys reach the editor
- Status bar (filename, line/column, mode) and message bar
- Command mode (`Ctrl-P`) with a structured parser
- Config loaded from `~/.config/text-editor/config.toml` or `--config`

## Text model

- Array-of-lines buffer (`list[str]`)
- Insert, delete, split/join lines, tab expansion
- Cursor movement with sticky column on vertical moves
- Viewport scrolling to keep the cursor visible

## File I/O

- UTF-8 open (BOM stripped); reject oversize files
- Atomic save (temp file, flush, fsync, replace)
- Preserve permissions and write through symlinks on POSIX
- Graceful errors for missing files, encoding failures, read-only targets, and failed writes
- Dirty-buffer warning before quit
- Mixed line endings in one file are normalized to the first detected style on load; save uses one configured ending
- `:write` / `Ctrl-S` skip disk I/O on a clean buffer; trailing-newline policy applies on the next save after an edit

## Undo / redo

- Reversible command objects with typed-character grouping
- Redo invalidated after new edits; bounded history depth

## Search

- Incremental find (`Ctrl-F`) anchored to the search start position
- Command-mode `:find`, `:next`, `:prev`
- Highlight current match; next/previous wrap around the match list
- Forward search from the anchor does **not** jump backward to earlier matches

## Commands

`:open`, `:write` / `:w`, `:saveas`, `:quit` / `:q`, `:quit!`, `:wq`, `:find`,
`:next`, `:prev`, `:goto`, `:set`, `:help`

## Testing and quality

- Headless unit tests for buffer, cursor, viewport, undo, search, file I/O, parser, config, dispatch, and render
- `ruff`, `mypy --strict`, and `pytest` in CI on Linux and Windows

See [ADR 0001](adr/0001-core-architecture-decisions.md), [ADR 0002](adr/0002-hardening-decisions.md),
and [ADR 0003](adr/0003-search-anchor-semantics.md) for design rationale.
