---
default_highlighter: oils-sh
---

Portability
===========

What does your platform need to run Oils?

These are some notes that supplement [INSTALL](INSTALL.html).

<div id="toc">
</div>

## Issues in the core of Oils

### libc - `FNM_EXTMATCH` is not in POSIX

To match extended globs like `@(*.cc|*.h)`, OSH relies on `FNM_EXTMATCH` from
GNU libc.

This is unlike bash, which has its own extended glob library.

TODO: when using other libc, using this syntax should be an error.

### libc - `GLOB_PERIOD` is not in POSIX

To implement the bash feature `shopt -s dotglob`, OSH relies on `GLOB_PERIOD`,
which some libc's implement.

This is unlike bash, which has its own glob library.

### Atomic Assignments

The signal handler assumes that int and pointer assignments are atomic.  This
is a common and widespread assumption.

- Related: [Atomic vs. Non-Atomic
  Operations](https://preshing.com/20130618/atomic-vs-non-atomic-operations/)
  by Jeff Preshing

<!--
As of 2024, the GC object layout doesn't depend on endian-ness.

Tagged pointers may change this.  A value may be either a pointer, which
implies its least significant bits are zero, or an immediate value.

We will have some #ifdef for it.
-->

## Extra Features

### USDT - Userland Statically-Defined Tracing

Our C++ code has `DTRACE_PROBE()` macros, which means we can use tools like
`bpftrace` on Linux to make low-overhead queries of runtime behavior.

The probe names and locations aren't stable across releases.

## "Enums" that are often extended

Different Unix implementations often extend:

- the list of signals 
- the list of [ulimit][] resources, which correspond to flags

[ulimit]: ref/chap-builtin-cmd.html#ulimit

## Unicode

Strings in Oils are byte strings, which are often UTF-8 encoded.

We use `libc` functions that may depend on the global locale setting, like
`glob()`.  We currently assume your libc is configured to use UTF-8.

See the [Unicode doc][] for details on Unicode-aware operations.

[Unicode doc]: unicode.html

## Related

- [INSTALL](INSTALL.html)
- [Oils Help Mirror](help-mirror.html)

<!--

TODO: ./configure could detect some of these
-->
