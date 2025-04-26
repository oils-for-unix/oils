---
in_progress: yes
---

The Unix Shell Process Model - When Are Processes Created?
=============

OSH and YSH are both extensions of POSIX shell, and share its underlying "process model".

Each Unix process has its **own** memory, that is not shared with other
processes.  (It's created by `fork()`, which means that the memory is
"copy-on-write".)

Understanding when a shell starts processes will make you a better shell
programmer.

As a concrete example, here is some code that behaves differently in
[bash]($xref) and [zsh]($xref):

   
    $ bash -c 'echo hi | read x; echo x=$x'
    x=

    $ zsh -c 'echo hi | read x; echo x=$x'
    x=hi

If you understand why they are different, then that means you understand the
process model!

(OSH behaves like zsh.)

---

Related: [Interpreter State](interpreter-state.html).  These two docs are the
missing documentation for shell!

<div id="toc">
</div>

## Shell Constructs That Start Processes

### Simple Command

    ls /tmp

### Pipelines `myproc | wc -l`

Affected by these options:

- `shopt -s lastpipe`
- `set -o pipefail`

Note that functions Can Be Transparently Put in Pipelines:

Hidden subshell:

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


## FAQ: "Subshells By Surprise"

Sometimes subshells have no syntax.

Common issues:

### shopt -s lastpipe

Mentioned in the intro:

    $ bash -c 'echo hi | read x; echo x=$x'
    x=

    $ zsh -c 'echo hi | read x; echo x=$x'
    x=hi

### Other Pipelines

    myproc (&p) | grep foo

## Process Optimizations - `noforklast`

Why does a Unix shell start processes?  How many processes are started?

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

## YSH Ideas

- Rich history: this feature may fork a process for each interactive line, with
  a PTY (rather than a pipe) connecting the processes
- The "pipecar" process to turn process completion events into pipe events?
  - Or perhaps we need general coroutines, like async/await

## Appendix: Non-Shell Tools

These Unix tools start processes:

- `xargs`
  - `xargs -P` starts parallel processes (but doesn't buffer output)
- `find -exec`
  - has a mechanism for batching, e.g. with `find . -exec echo {} +` vs. `\;`
- `make`
  - `make -j` starts parallel processes (but doesn't buffer output)
  - there is the "job server protocol", which works across child processes,
    e.g. grandchildren and more
- `ninja` (buffers output)
- `init` - the process supervisor
