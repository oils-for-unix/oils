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

### _status

Set by the `try` builtin.

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

### _pipeline_status

Alias for [PIPESTATUS]($osh-help).

### _process_sub_status

The exit status of all the process subs in the last command.

## YSH Tracing

### SHX_indent

### SHX_punct

### SHX_pid_str


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

## Platform

### OILS_VERSION

The version of Oil that is being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

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

### YSH_HISTFILE

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

### _reply

YSH read sets this:

    read --line < myfile

    read --all < myfile

## Functions

### RANDOM

bash compat

### SECONDS

bash compat

