---
in_progress: true
default_highlighter: oil-sh
---

Builtin Reference
===================

TODO: Builtins By Category

<!-- TODO: should run all this code as in tour.md -->

<div id="toc">
</div>

## I/O Builtins

### read

## Appendix

### Builtins That Modify Interpreter State

- `shopt`
  - deprecated `set`
- `shvar` (temp bindings)
- `push-registers`
- Not scoped:
  - technically `trap`
  - `hash` and `hash -d`
  - discouraged: `alias` and `unalias`
  - `getopts` deals with mutable globals

- TODO: `push-procs`

That check interpreter state:

- `use dialect` checks `_DIALECT`.
