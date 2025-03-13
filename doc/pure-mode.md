---
default_highlighter: oils-sh
in_progress: true
---

Oils Pure Mode: For Config Files and Functions
=========================================

The interpreter can run in pure mode


<div id="toc">
</div>

## Why?

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

## Where is Pure Mode Active?

### `--eval-pure` 

vs `--eval`

TODO: link to doc/reef

### `eval()` and `evalExpr()`

vs. `io->eval()` and `io->evalExpr()`

TODO: link to doc/reef

### Pure Functions

- TODO: `func`

## What's Allowed in Pure Mode?

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
