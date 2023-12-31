---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

Special Variables
===

This chapter in the [Oils Reference](index.html) describes special variables
for OSH and YSH.

<div id="toc">
</div>

## YSH Vars

### ARGV

Replacement for `"$@"`

### ENV

TODO

### _this_dir

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

## YSH Status

### `_status`

An `Int` that's set by the `try` builtin.

    try {
      ls /bad  # exits with status 2
    }
    if (_status !== 0) {  # _status is 2
      echo 'failed'
    }

### `_error`

A `Dict` that's set by the `try` builtin when catching certain errors.

Such errors include JSON/J8 encoding/decoding errors, and user errors from the
`error` builtin.

    try {
      echo $[toJ8( /d+/ )]  # invalid Eggex type
    }
    echo "failed: $[_error.message]"  # => failed: Can't serialize ...

### `_pipeline_status`

Alias for [PIPESTATUS]($osh-help).

### `_process_sub_status`

The exit status of all the process subs in the last command.

## YSH Tracing

### SHX_indent

### SHX_punct

### SHX_pid_str

## YSH Read

### _reply

YSH read sets this:

    read --line < myfile

    read --all < myfile

## Oils VM

### `OILS_VERSION`

The version of Oils that's being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

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

## Other Env

### HOME

$HOME is used for:

1. ~ expansion 
2. ~ abbreviation in the UI (the dirs builtin, \W in $PS1).

Note: The shell doesn't set $HOME.  According to POSIX, the program that
invokes the login shell sets it based on /etc/passwd.

### PATH

A colon-separated string that's used to find executables to run.


## POSIX Special

## Other Special

### BASH_REMATCH

Result of regex evaluation `[[ $x =~ $pat ]]`.

### PIPESTATUS

Exit code of each element in a pipeline.


## Call Stack

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

