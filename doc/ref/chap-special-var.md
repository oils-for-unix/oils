---
title: Special Variables (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Special Variables**

</div>

This chapter describes special variables for OSH and YSH.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## YSH Vars

### ARGV

Replacement for `"$@"`

### ENV

An `Obj` that's populated with environment variables.  Example usage:

    var x = ENV.PYTHONPATH
    echo $[ENV.SSH_AUTH_SOCK]
    setglobal ENV.PYTHONPATH = '.'

It's initialized exactly **once** per process, in any of these situations:

1. At shell startup, if `shopt --set env_obj` is on.  This is true when invoking
   `bin/ysh`.
2. When running `bin/osh -o ysh:upgrade` or `ysh:all`.
3. When running `shopt --set ysh:upgrade` or `ysh:all`.

Related: [ysh-shopt][], [osh-usage][]

[ysh-shopt]: chap-builtin-cmd.html#ysh-shopt
[osh-usage]: chap-front-end.html#osh-usage

---

When launching an external command, the shell creates a Unix `environ` from the
`ENV` Obj.  This means that mutating it affects all subsequent processes:

    setglobal ENV.PYTHONPATH = '.'
    ./foo.py
    ./bar.py

You can also limit the change to a single process, without `ENV`:

    PYTHONPATH=. ./foo.py
    ./bar.py               # unaffected

---

YSH reads these ENV variables:

- `PATH` - where to look for executables
- `PS1` - how to print the prompt
- TODO: `PS4` - how to show execution traces
- `YSH_HISTFILE` (`HISTFILE` in OSH) - where to read/write command history
- `HOME` - for tilde substitution ([tilde-sub])

[tilde-sub]: chap-word-lang.html#tilde-sub

### `__defaults__`

The shell puts some default settings in this `Dict`.  In certain situations, it
consults `__defaults__` after consulting `ENV`.  For example:

- if `ENV.PATH` is not set, consult `__defaults__.PATH`
- if `ENV.PS1` is not set, consult `__defaults__.PS1`

<!-- TODO: consider renaming to DEF.PS1 ? -->

### `__builtins__`

An object that contains names visible in every module.

If a name is not visible in the local scope, or module global scope, then it's
looked up in `__builtins__`.

### `_this_dir`

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

## YSH Status

### `_status`

DEPRECATED: Use `_error.code` instead.

### `_error`

A `Dict` that's set by the `try` builtin.

The integer `_error.code` is always present:

    try {
      ls /tmp
    }
    echo "status is $[_error.code]"

Some errors also have a `message` field, like JSON/J8 encoding/decoding errors,
and user errors from the [error][] builtin.

    try {
      echo $[toJson( /d+/ )]  # invalid Eggex type
    }
    echo "failed: $[_error.message]"  # => failed: Can't serialize ...

[error]: chap-builtin-cmd.html#error


### `_pipeline_status`

After a pipeline of processes is executed, this array contains the exit code of
each process.

Each exit code is an [Int](chap-type-method.html#Int).  Compare with
[`PIPESTATUS`](#PIPESTATUS).

### `_process_sub_status`

The exit status of all the process subs in the last command.

## YSH Tracing

### SHX_indent

### SHX_punct

### SHX_pid_str

## YSH Read

### _reply

Builtins that `read` set this variable:

    read --all < foo.txt
    = _reply  # => 'contents of file'

    json read < foo.json
    = _reply  # => (Dict)  {}

## Oils VM

### `OILS_VERSION`

The version of Oils that's being run, e.g. `0.23.0`.

<!-- TODO: specify comparison algorithm. -->

### `LIB_OSH`

The string `///osh`, which you can use with the [source][] builtin.

    source $LIB_OSH/two.sh    

[source]: chap-builtin-cmd.html#source

### `LIB_YSH`

The string `///ysh`, which you can use with the [source][] builtin.

    source $LIB_YSH/yblocks.ysh

[source]: chap-builtin-cmd.html#source

### `OILS_GC_THRESHOLD`

At a GC point, if there are more than this number of live objects, collect
garbage.

### `OILS_GC_ON_EXIT`

Set `OILS_GC_ON_EXIT=1` to explicitly collect and `free()` before the process
exits.  By default, we let the OS clean up.

Useful for ASAN testing.

### `OILS_GC_STATS`

When the shell process exists, print GC stats to stderr.

### `OILS_GC_STATS_FD`

When the shell process exists, print GC stats to this file descriptor.

## Float

### NAN

The float value for "not a number".

(The name is consistent with the C language.)

### INFINITY

The float value for "infinity".  You can negate it to get "negative infinity".

(The name is consistent with the C language.)

## Module

### `__provide__`

A module is evaluated upon `use`.  After evaluation, the names in the
`__provide__` `List` are put in the resulting module `Obj` instance.

<!--
`__provide__` may also be a string, where 'p' stands for --procs, and 'f' stands for funcs.

Or we could make it [1, 2] insetad
-->

## POSIX Special

`$@  $*  $#     $?  $-     $$  $!   $0  $9`

## Shell Vars

### IFS

Used for word splitting.  And the builtin `shSplit()` function.

### LANG

TODO: bash compat

### GLOBIGNORE

TODO: bash compat

## Shell Options

### SHELLOPTS

bash compat: serialized options for the `set` builtin.

### BASHOPTS

bash compat: serialized options for the `shopt` builtin.

(Not implemented.)

## Other Env

### HOME

The `$HOME` env var is read by the shell, for:

1. `~` expansion 
2. `~` abbreviation in the UI (the dirs builtin, `\W` in `$PS1`).

The shell does not set $HOME.  According to POSIX, the program that invokes the
login shell should set it, based on `/etc/passwd`.

### PATH

A colon-separated string that's used to find executables to run.

In YSH, it's `ENV.PATH`.

## Other Special

### BASH_REMATCH

Result of regex evaluation `[[ $x =~ $pat ]]`.

### PIPESTATUS

After a pipeline of processes is executed, this array contains the exit code of
each process.

Each exit code is a [Str](chap-type-method.html#Str).  Compare with
[`_pipeline_status`](#_pipeline_status).

## Platform

### HOSTNAME

The name of the "host" or machine that Oils is running on, determined by
`gethostname()`.

### OSTYPE

The operating system that Oils is running on, determined by `uname()`.

Examples: `linux darwin ...`

## Call Stack

### BASH_SOURCE

### FUNCNAME

### BASH_LINENO

## Tracing

### LINENO

## Process State

### BASHPID

TODO

### PPID

TODO

### UID

### EUID

## Process Stack

## Shell State

## Completion

### COMP_WORDS

An array of words, split by : and = for compatibility with bash.  New
completion scripts should use COMP_ARGV instead.

### COMP_CWORD

Discouraged; for compatibility with bash.

### COMP_LINE

Discouraged; for compatibility with bash.

### COMP_POINT

Discouraged; for compatibility with bash.

### COMP_WORDBREAKS

Discouraged; for compatibility with bash.

### COMPREPLY

User-defined completion functions should Fill this array with candidates.  It
is cleared on every completion request.

### COMP_ARGV

An array of partial command arguments to complete.  Preferred over COMP_WORDS.
The compadjust builtin uses this variable.

(An OSH extension to bash.)

## History

### HISTFILE

Override the default OSH history location.

### YSH_HISTFILE

Override the default YSH history location.

## Interactive

### OILS_COMP_UI

Set which completion UI to use. Defaults to `minimal`.

- `minimal` - a UI that approximates the default behavior of GNU readline.
- `nice` - a UI with a fancy pager and a prompt with horizontal scrolling instead of wrapping.

This variable is currently only checked once during shell initialization.

## cd

### PWD

### OLDPWD

### CDPATH

## getopts

### OPTIND

### OPTARG

### OPTERR

## read

### REPLY

OSH read sets this:

    read < myfile

## Functions

### RANDOM

bash compat

### SECONDS

bash compat

