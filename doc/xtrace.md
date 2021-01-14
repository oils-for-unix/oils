---
in_progress: yes
default_highlighter: oil-sh
---

Tracing Execution in Oil (xtrace)
==================================

Oil extends shell's `set -x` to give you more visibility into your program's
execution.

<div id="toc">
</div>

## Background

In shell, the `$PS4` variable controls the prefix of each trace line.  The
default value is `'+ '`, which results in traces like:

    + echo 1
    + echo 2


## Oil Enhancements

In Oil, the default is

    PS4='${X_indent}${X_punct}${X_pid} '

- `X_indent` is affected by proc invocations, `source`, and `eval`
- `X_punct` is:
  - `+` for a command (TODO: make this richer?)
  - `>` and `<` for indentation changes -- **synchronous**
  - `|` and `.` for process start and stop -- **asynchronous**, e.g. with
    pipelines and `&`.

To see hierarchical traces, turn on [xtrace_rich]($oil-help):

    shopt -s xtrace_rich   # part of the oil:basic option group

## Useful Variables For Use in `$PS4`

- `@BASH_SOURCE`, `@FUNCNAME`, `$LINENO`
  - TODO: Add `@SOURCE_NAME` as alias?
- TODO: `$SECONDS` for timing

<!--
And OIL_PID?  or maybe OIL_CURRENT_PID.  or maybe getpid() is better -
distinguish between functions and values
-->

## Parsing `xtrace_rich` Output

- It's concurrent, but lines are atomically written
- TODO: Specify a regular language?
- Coalesce by PID?
