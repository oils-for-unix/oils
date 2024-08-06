---
in_progress: yes
---

Process Model
=============

Why does a Unix shell start processes?  How many processes are started?

Related: [Interpreter State](interpreter-state.html).  These two docs are the
missing documentation for shell!

<div id="toc">
</div>

## Shell Constructs That Start Processes

### Pipelines

- `shopt -s lastpipe`
- `set -o pipefail`

#### Functions Can Be Transparently Put in Pipelines

Implicit subshell:

    { echo 1; echo 2; } | wc -l

A `SubProgramThunk` is started for the LHS of `|`.

### Command Sub `d=$(date)`

    d=$(date)   

### Process Sub `<(sort left.txt)`

    diff -u <(sort left.txt) <(sort right.txt)

### Async - `fork` or `sleep 2 &`

### Explicit Subshell - `forkwait` or `( echo hi )`

Explicit Subshells are Rarely Needed.

- prefer `pushd` / `popd`, or `cd { }` in YSH.

## Process Optimizations - `noforklast`

Bugs / issues

- job control:
  -  restoring process state after the shell runs
  - `sh -i -c 'echo hi'`
- traps
  - not run - issue #1853
- Bug with `set -o pipefail` 
  - likewise we have to disable process optimizations for `! false` and
    `!  false | true`

Oils/YSH specific:

- `shopt -s verbose_errexit`
- crash dump
  - because we don't get to test if it failed
- stats / tracing - counting exit codes

## Process State

### Redirects


## Builtins

### [wait]($help)

### [fg]($help)

### [bg]($help)

### [trap]($help)


## Appendix: Non-Shell Tools

- `xargs` and `xargs -P`
- `find -exec`
- `make -j`
  - doesn't do anything smart with output
- `ninja`
  - buffers output too
