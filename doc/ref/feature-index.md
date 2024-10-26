---
title: YSH and OSH Topics by Feature
all_docs_url: ..
default_highlighter: oils-sh
preserve_anchor_case: yes
---

YSH and OSH Topics by Feature
====

<span class="in-progress">(in progress)</span>

This page links to topics in the [Oils Reference](index.html).  It's organized
differently than the [YSH Table of Contents](toc-ysh.html) or [OSH Table of
Contents](toc-osh.html).

<div id="toc">
</div>

## Errors

- [try](chap-builtin-cmd.html#try)
- `_error`

Status:

- `_pipeline_status`
- `_process_sub_status`

OSH:

- `$?` - not idiomatic in YSH

## Environment Variables

YSH:

- `ENV`
- `simple-command` - for `FOO=bar` bindings
- TODO: should we have a `envFromDict()` function that goes with `env -i`?

OSH:

- `export`

## I/O

YSH:

- `write` 
  - `echo` is a shortcut for `write`
- `ysh-read` -- covers `read --all`
- `redir`
- the `io` Object


## Modules

- use
- `is-main`
- provide
- `__provide__`
- A module becomes an `Obj` with `__invoke__`

OSH:

- `source`
- `source-guard`

## Objects

- `Obj`
- `first() rest()`
- operator `.`
- operator `->`

## Closures

- blocks
- procs and funcs?

## Procs

- `proc-def`
- `__invoke__` and `Obj`
- simple-command invokes procs

## Funcs

- `func-def`
- `__call__` and `Obj`
- call expression

## Reflection

- `io` object has `eval` etc.
- the `vm` object

## Unicode

- TODO: which functions respect Unicode?

## Interactive Shell

- `renderPrompt()`

OSH:

- `complete`
- Oils enhancements: `compexport` `compadjust` 
