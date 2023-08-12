---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Special Variables
===

This chapter in the [Oils Reference](index.html) describes special variables
for OSH and YSH.

<div id="toc">
</div>

## Shell Vars

### `ARGV`

Replacement for `"$@"`

### `_DIALECT`

Name of a dialect being evaluated.

### `_this_dir`

The directory the current script resides in.  This knows about 3 situations:

- The location of `oshrc` in an interactive shell
- The location of the main script, e.g. in `osh myscript.sh`
- The location of script loaded with the `source` builtin

It's useful for "relative imports".

## Platform

### OIL_VERSION

The version of Oil that is being run, e.g. `0.9.0`.

<!-- TODO: specify comparison algorithm. -->

## Exit Status


### `_status`

Set by the `try` builtin.

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

### `_pipeline_status`

Alias for [PIPESTATUS]($osh-help).

### `_process_sub_status`

The exit status of all the process subs in the last command.

## Tracing

### SHX_indent

### SHX_punct

### SHX_pid_str


<h2 id="env">Environment Variables</h2>

### Shell Options

<!-- CONFLICT: Duplicates the above -->

<h4 id="SHELLOPTS">SHELLOPTS</h4>

For the 'set' builtin.

<h4 id="BASHOPTS">BASHOPTS</h4>

For the 'shopt' builtin.

<h3>Other Env</h3>

<h4 id="HOME">HOME</h4>

$HOME is used for:

1. ~ expansion 
2. ~ abbreviation in the UI (the dirs builtin, \W in $PS1).

Note: The shell doesn't set $HOME.  According to POSIX, the program that
invokes the login shell sets it based on /etc/passwd.

<h4 id="PATH">PATH</h4>

A colon-separated string that's used to find executables to run.

<h4 id="IFS">IFS</h4>

Used for word splitting.  And the builtin split() function.

<h3>Oil Paths</h3>

<h2 id="special">Special Variables</h2>

### Special

### POSIX Special

### Other Special

### Oil Special

### Platform

### Call Stack

### Tracing

### Process State

### Process Stack

### Shell State

<h3>Completion</h3>

<h4 id="COMP_WORDS">COMP_WORDS</h4>

An array of words, split by : and = for compatibility with bash.  New
completion scripts should use COMP_ARGV instead.

<h4 id="COMP_CWORD">COMP_CWORD</h4>

Discouraged; for compatibility with bash.

<h4 id="COMP_LINE">COMP_LINE</h4>

Discouraged; for compatibility with bash.

<h4 id="COMP_POINT">COMP_POINT</h4>

Discouraged; for compatibility with bash.

<h4 id="COMPREPLY">COMPREPLY</h4>

User-defined completion functions should Fill this array with candidates.  It
is cleared on every completion request.

<h4 id="COMP_ARGV">COMP_ARGV</h4>

An array of partial command arguments to complete.  Preferred over COMP_WORDS.
The compadjust builtin uses this variable.

(An OSH extension to bash.)

<h3>Functions</h3>


### Other Special

