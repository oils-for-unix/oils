---
default_highlighter: oils-sh
in_progress: true
---

Oils Pure Mode: For Config Files and Functions
=========================================

The interpreter can run in pure mode


<div id="toc">
</div>

## Why does Oils have Pure Mode?

- config files should be isolated to git
- **data** versus **code**

---

- JSON is data.
  - TSV, HTML is data
  - J8 Notation is data.
- Hay is programmable data.
  - it doesn't format your hard drive.

### WebAssembly Analogy

WebAssembly is also pure computation, and can be used in a variety of contexts.

It has `io` too.

## When is it active?

### `--eval-pure` 

vs `--eval`

TODO: link to doc/reef

### `eval()` and `evalExpr()`

vs. `io->eval()` and `io->evalExpr()`

TODO: link to doc/reef

### Pure Functions

- TODO: `func`

## What's allowed in Pure Mode?  Not allowed?

What's not allowed:

- external commands
- any process construct
  - pipelines
  - subshell
  - command sub and process sub
  - background jobs with `&`
- many builtins
  - most of these do I/O
- globbing - touches the file system
- time and randomness
  - $SECONDS and $RANDOM

---

- [`shell-flags`](chap-front-end.html#shell-flags) for `--eval-pure`
- [`func/eval`](chap-builtin-func.html#func/eval) and
  [`func/evalExpr`](chap-builtin-func.html#func/evalExpr)
- [`func`](chap-ysh-cmd.html#func) - functions are pure
- [`io`](chap-type-method.html#io) and [`vm`](chap-type-method.html#vm) - impure
  behavior is attached to these objects

## Notes

Pure mode is a bit like functional programming, but the style **inside** a
function is not functional.

In YSH, it's natural to write pure functions in an imperative style.  Just like
you can do this in Python or JavaScript (although there is no enforcement,
unlike Oils)




