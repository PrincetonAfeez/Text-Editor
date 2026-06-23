# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-06-22

### Added

- Curses-based terminal text editor with command mode, undo/redo, and search
- Atomic UTF-8 file I/O with configurable line endings and trailing newline policy
- Headless test suite, CI on Linux/Windows, and architecture decision records

### Fixed

- Search no longer jumps backward when no match exists at or after the anchor
- Failed saves no longer mutate in-memory `trailing_newline` before a successful write
- `:set keymap_name=…` takes effect immediately; `:set search_case_sensitive=…` refreshes matches
- `:open` on a missing path creates a new buffer, matching CLI startup behavior
- Read-only save failures report a dedicated message
- Status bar column reflects visual (tab-aware) position
- `:quit` on a dirty buffer returns a failure indication to command dispatch

### Fixed (round 2)

- Failed saves no longer mutate in-memory `line_ending` before a successful write
- `find_query()` returns `False` when no forward match is selected
- `find_previous` from an unset match index lands on the last match
- Read permission failures report the same dedicated message as save
- Post-read size guard closes the stat/read TOCTOU gap for oversized files
- `:wq` skips save when the buffer is already clean
- Horizontal movement preserves sticky column; unknown keymaps are rejected in `:set`
- New files on POSIX receive `666 & ~umask` instead of `0600`

### Fixed (round 3)

- `:open` on a directory reports `not a regular file` instead of a permission error
- `:write` and `Ctrl-S` skip disk I/O when the buffer is already clean
- Command/search prompt cursor placement is display-width aware
- Search navigation preserves the sticky column
- Removed unused mutating `apply_line_ending_policy()` helper
- README and config docs aligned on keymap validation behavior
