# ADR 0003: Search Anchor Semantics
 
## Status

Accepted.

## Context

Search is available from an incremental prompt (`Ctrl-F`) and from command mode
(`:find`). Both need a consistent rule for which match is selected when several
matches exist in the buffer.

Wrap-around is desirable for `:next` and `:prev`, but jumping backward on the
initial search contradicts the incremental prompt contract: the cursor should stay
anchored to where the search started unless a match exists at or after that
position.

## Decision

1. **`index_at_or_after()`** returns the first match at or after `(row, col)`, or
   `-1` when no such match exists. It does not wrap to the start of the file.

2. **`find_query()`** uses an optional anchor (the search start for incremental
   find). When the forward index is `-1`, the cursor stays put and the message bar
   reports `not found`.

3. **`find_next()` / `find_previous()`** continue to wrap through the match list
   with modulo indexing.

4. **`:set search_case_sensitive=…`** recomputes the active match list and
   re-anchors from the current cursor position.

## Consequences

- Incremental search no longer jumps to an earlier line while the user types.
- `:next` still reaches earlier matches after the first explicit navigation step.
- Tests cover forward-only anchoring separately from wrap navigation.
