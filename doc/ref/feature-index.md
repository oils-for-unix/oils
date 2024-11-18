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

## Where YSH Improves on OSH

### Errors

YSH:

- [`try`](chap-builtin-cmd.html#try)
- [`_error`](chap-special-var.html#_error)
- multiple processes
  - [`_pipeline_status`](chap-special-var.html#_pipeline_status)
  - [`_process_sub_status`](chap-special-var.html#_process_sub_status)
- [Options](chap-option.html):
  - `strict_errexit`, `command_sub_errexit`, ...

OSH:

- [`$?`](chap-special-var.html#POSIX-special) - not idiomatic in YSH
- [Options](chap-option.html):
  - `errexit`, `pipefail`, `inherit_errexit`

### Environment Variables

YSH:

- [`ENV`][ENV]
- [`ysh-prefix-binding`][ysh-prefix-binding] - for `NAME=val` env bindings
- [`simple-command`][simple-command] - external commands are started with an
  `environ`
- [Options](chap-option.html):
  - `shopt --unset no_exported`
  - `shopt --set env_obj`

[ENV]: chap-special-var.html#ENV

<!--
TODO: should we have a `envFromDict()` function that goes with `env -i`?
-->

OSH:

- [`export`](chap-osh-assign.html#export)
- [`prefix-binding`][prefix-binding] - for `NAME=val` env bindings

[prefix-binding]: chap-cmd-lang.html#prefix-binding
[ysh-prefix-binding]: chap-cmd-lang.html#ysh-prefix-binding

[simple-command]: chap-cmd-lang.html#simple-command


### I/O

YSH:

- [`write`](chap-builtin-cmd.html#write)
  - [`ysh-echo`](chap-builtin-cmd.html#ysh-echo) is a shortcut for `write`
- [`ysh-read`](chap-builtin-cmd.html#ysh-read) - `read --all`, etc.
- [`redir`](chap-builtin-cmd.html#redir)
- The [`io`](chap-type-method.html#io) object

OSH:

- [`printf`](chap-builtin-cmd.html#printf)

### Procs

YSH:

- [`proc`](chap-ysh-cmd.html#proc)
- Invokable objects: [`__invoke__`][__invoke__], [`Obj`][Obj]
- [`simple-command`][simple-command] is how you invoke procs

OSH:

- [`sh-func`](chap-cmd-lang.html#sh-func)

### Modules

- [`use`](chap-builtin-cmd.html#use)
- [`is-main`](chap-builtin-cmd.html#is-main)
- provide (TODO)
- [`_this_dir`](chap-special-var.html#_this_dir)
- [`__provide__`](chap-special-var.html#__provide__)
- An imported module is an [`Obj`][Obj] with an [`__invoke__`][__invoke__]
  method

[Obj]: chap-type-method.html#Obj
[__invoke__]: chap-type-method.html#__invoke__

OSH:

- [`source`](chap-builtin-cmd.html#source)
- [`source-guard`](chap-builtin-cmd.html#source-guard)

### Interactive Shell

- [`renderPrompt()`](chap-plugin.html#renderPrompt)

OSH:

- [`complete`][complete]
- Oils enhancements: [`compexport`][compexport], [`compadjust`][compadjust]

[complete]: chap-builtin-cmd.html#complete
[compadjust]: chap-builtin-cmd.html#compadjust
[compexport]: chap-builtin-cmd.html#compexport

### Tracing

- `set -x` aka `set -o xtrace`
- [PS4][]
- `SHX_*`

[PS4]: chap-plugin.html#PS4

### Unicode

- TODO: which functions respect Unicode?

Also see [the Unicode doc](../unicode.html).


## YSH Only

### Objects

- [`Obj`][Obj]
  - `__invoke__` and `__call__`
  - `propView()` and `prototype()` - may be renamed `first() rest()`
  - [`ENV`][ENV] is an `Obj`
- operator `.` [ysh-attr](chap-expr-lang.html#ysh-attr)
- operator `->` [thin-arrow](chap-expr-lang.html#thin-arrow)

### Closures

- [block-arg](chap-cmd-lang.html#block-arg)
- Maybe: proc, func

### Funcs

- [`func`](chap-ysh-cmd.html#func)
- Callable objects: [`__call__`][__call__] and [`Obj`][Obj] (TODO)
- [`ysh-func-call`](chap-expr-lang.html#ysh-func-call)

[__call__]: chap-type-method.html#__call__

### Reflection

- The [`io`][io] object has `eval()` methods, etc.
- The [`vm`][vm] object for inspecting interpreter structures

[io]: chap-type-method.html#io
[vm]: chap-type-method.html#vm

### Namespaces

- [`ENV`](chap-special-var.html#ENV)
- [`__builtins__`](chap-special-var.html#__builtins__)

<!--

TODO:

- __modules__
- does vm.getFrame() belong?

-->


