# ADR 0002: Hardening and Edge-Case Decisions

## Status

Accepted.

## Context

After the core editor (ADR 0001) was complete and tested, a series of review
passes hardened the terminal and file boundaries and added input-robustness for
files the editor did not originally anticipate. This record captures the
decisions that have lasting architectural weight.

## Decisions

### 1. Raw mode for control keys

The input loop puts the terminal in `curses.raw()` rather than `cbreak()`. In
cbreak mode the tty keeps flow control and job control, so `Ctrl-S` (XOFF),
`Ctrl-Q` (XON), and `Ctrl-Z` (SIGTSTP) never reach the editor on Unix. Raw mode
delivers them as ordinary key events, which the data-driven keymap then routes.

### 2. Atomic save preserves the original file's identity

The save path already wrote to a temporary file and `os.replace`d it. It now
also (a) copies the original file's permission bits onto the replacement, since
`mkstemp` creates the temp as `0600` and would otherwise strip modes such as the
executable bit; (b) resolves symlinks with `os.path.realpath` so a save writes
through to the link target instead of replacing the link; and (c) fsyncs the
target directory on POSIX so the rename itself is durable, not just the bytes.

### 3. Trailing newline is a configured policy

Saves end the file with a newline by default (`ensure_trailing_newline`), matching
the POSIX convention and keeping diffs clean. It is configurable because some
files are intentionally newline-free. Content edits never silently add or drop the
newline; only the save path applies the policy.

### 4. Display width is centralized and wide-character aware

A curses-free `display` module owns terminal-width math: tab expansion, East
Asian wide characters (two columns), and replacement of C0/C1 control characters
with a visible placeholder so a file containing escape sequences cannot corrupt
the terminal. Cursor placement, sticky-column movement, scrolling, and rendering
all consult the same functions, so the model stays internally consistent. Full
grapheme-cluster and zero-width-combining support remains out of scope.

### 5. Search is incremental

The find prompt searches as each character is typed (anchored to where the search
began) and highlights the current match live; cancelling restores the original
cursor position. The prompt gained a generic `on_change` callback so this stays a
thin layer over the existing command, not a special case in the input loop.

### 6. Undo history is bounded

The reversible-edit history caps its depth and drops the oldest edits, bounding
memory on long sessions while preserving the command-pattern design.

## Consequences

These changes are mostly at the edges (file I/O, terminal setup, display math)
and keep the core buffer/cursor/undo model untouched. Behaviours that depend on
the host platform (POSIX file modes, symlinks, directory fsync) are guarded so
the editor still runs cleanly on Windows, and their tests skip where the
semantics do not apply.
