---
in_progress: yes
default_highlighter: oil-sh
---

Tracing Execution in Oil (xtrace)
==================================

Oil extends shell's `set -x` to give you more visibility into your program's
execution.  It shows you a trace with both static program structure (procs,
source, eval) and runtime events (starting and stopping Unix processes).

<div id="toc">
</div>

## Background

In shell, the `$PS4` variable controls the prefix of each trace line.  The
default value is `'+ '`, which results in traces like this:

    $ sh -c 'set -x; echo 1; echo 2'
    + echo 1
    1
    + echo 2
    2

## Oil Enhancements

The `oil:basic` option group turns on [xtrace_rich]($oil-help) and turns off
[xtrace_details]($oil-help).  In other words,

    shopt --set xtrace_rich
    shopt --unset xtrace_details

### Options

In Oil, the default is

    PS4='${SHX_indent}${SHX_punct}${SHX_pid_str} '

`SHX_indent` is affected by proc invocations, `source`, and `eval`, and new
processes.

`SHX_pid_str` is only set for child processes.

`SHX_punct` is:

- `+` for legacy shell tracing (`xtrace_details`)
  - proc calls, eval, and source
  - pipeline and wait
- `.` for `builtin` and `exec`
- `>` and `<` for **synchronous** constructs
- `|` and `;` for process start and stop -- **asynchronous**, e.g. with
  pipelines and `&`.
  - synchronous processes: subshell, command sub, command (;)
  - async processes: fork (&), pipeline parts, process sub, here doc

TODO: `SHX_descriptor` is alias for `BASH_XTRACEFD` ?

## Useful Variables For Use in `$PS4`

- `@BASH_SOURCE`, `@BASH_LINENO`, `@FUNCNAME`, `$LINENO`
  - TODO: Add `@SOURCE_NAMES` as alias?  `LINE_NUMS`?
- TODO: `$SECONDS` for timing

<!--
And OIL_PID?  or maybe OIL_CURRENT_PID.  or maybe getpid() is better -
distinguish between functions and values
-->

## Parsing `xtrace_rich` Output

- It's concurrent, but lines are atomically written
- TODO: Specify a regular language?
- Coalesce by PID?
