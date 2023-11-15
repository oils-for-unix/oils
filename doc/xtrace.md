---
default_highlighter: oil-sh
---

Tracing Execution in YSH (`xtrace`)
===================================

YSH extends shell's `set -x` / `xtrace` mechanism to give you more visibility
into your program's execution.  It shows high-level program structure
("functions", `eval`) as well as runtime events (starting and stopping external
processes).

<div id="toc">
</div>

## Background

In shell, the `$PS4` variable controls the prefix of each trace line.  The
default value is `'+ '`, which results in traces like this:

    $ sh -x -c 'echo 1; echo 2'
    + echo 1
    1
    + echo 2
    2

### What's Wrong With `set -x`?

- It shows only an `argv` array for commands.  It doesn't tell you if the
  command is a builtin, shell function, or external binary, which is important
  for program comprehension (and performance).
- It doesn't show you which commands are run in **which processes**.  Because
  processes have their own state, this is also crucial for understanding a
  shell program.  (Example: does `echo x | read` mutate a variable?)
- It's **missing** other information, like when processes are started and
  stopped, the exit status, and when commands come from `eval` or `source`.
- Shell **concurrency** makes the trace incomprehensible.  For example, partial
  lines can be interleaved.
- Most implementations don't show non-printable and whitespace characters in a
  coherent way.

<!-- TODO: you generally lose tracing across processes. -->

## YSH Enhancements

YSH solves these problems.  Here's an example of tracing a builtin, a pipeline,
then another builtin:

    $ osh -O ysh:upgrade -x -c 'set +e; ls | grep OOPS | wc -l; echo end'
    . builtin set '+e'
    > pipeline
      | part 103
        . 103 exec ls
      | part 104
        . 104 exec grep OOPS
      | command 105: wc -l
      ; process 103: status 0
      ; process 104: status 1
      ; process 105: status 0
    < pipeline
    . builtin echo end

- Builtins are shown with the `builtin` prefix.
- External commands are shown with the `command` prefix.
- Bare `exec()` calls are shown with the `exec` prefix.
- It shows **synchronous** shell constructs with indentation and the `>`
  and `<` characters.  This includes the entire pipeline, as well as `proc`
  calls (not shown).
- It shows process starts and ends with the `|` and `;` characters.  These are
  **asynchronous** in general.
- It shows the exit status of **every process**, which is important for
  reasoning about failure.
- It annotates trace lines with the shell PID (when it's not the root PID).
- Strings in `argv` arrays may be quoted with [QSN]($oil-doc:qsn.html).  This
  shows special characters unambiguously, and ensures that each trace entry is
  exactly one physical line.

### Option Names

This functionality is enabled by the [xtrace_rich]($oil-help) option, but you
should generally use the `ysh:upgrade` option group.  This group turns on
[xtrace_rich]($oil-help) and turns off [xtrace_details]($oil-help), which  is
equivalent to:

    $ shopt --set xtrace_rich
    $ shopt --unset xtrace_details

### Variables for the Trace Line

In YSH, the default trace line prefix is:

    $ PS4='${SHX_indent}${SHX_punct}${SHX_pid_str} '

- `SHX_indent` is affected by synchronous constructs like `proc` and `eval`, as
  well as new processes.
- `SHX_pid_str` is only set for child shell processes (to avoid redundancy).
  It has a space at the beginning like `' 123'`.

`SHX_punct` is one of the following:

- `+` for legacy shell tracing ([xtrace_details]($oil-help))
- `.` for `builtin` and `exec`
- `>` and `<` for internal, stack-based, **synchronous** constructs
  - `proc`, `eval`, and `source`, an entire pipeline, and the `wait` builtin
  - running trap handlers (which happens in the main loop)
- `|` and `;` for process start and wait
  - **synchronous** processes: subshell aka [forkwait]($oil-help), command sub
    like `$(date)`, simple commands (`;`)
  - **async** processes: [fork]($oil-help) (`&`), pipeline parts, process subs
    like `<(sort left.txt)`, the process that writes a here doc

TODO: Cross-shell tracing

- `SHX_descriptor` is alias for `BASH_XTRACEFD` ?
- Inherited `$SHX_indent` and `$SHX_pid_str`

## Other Useful Variables

These variables can enhance the traces.

- `@BASH_SOURCE`, `@BASH_LINENO`, `@FUNCNAME`, `$LINENO`
  - TODO: Add `@SOURCE_NAMES` as alias?  `LINE_NUMS`?
- TODO: `$SECONDS` for timing

<!--
And OIL_PID?  or maybe OIL_CURRENT_PID.  or maybe getpid() is better -
distinguish between functions and values
-->

## Parsing `xtrace_rich` Output

TODO

- It's concurrent, but lines are atomically written
- Specify a regular language?
- Coalesce by PID?

