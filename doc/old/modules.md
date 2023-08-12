---
default_highlighter: oil-sh
in_progress: true
css_files: ../../web/base.css ../../web/manual.css ../../web/toc.css
---

Oil Modules Safely Separate a Program Into Files
================================================

Oil has a minimal module system that is shell-like.

- "Modules" is actually a misnomer because they are NOT "modular".  Procs are
modular.  But we use the term since "module" is sometimes associated with
file".
- In contrast to other features, it's very different than Python or JavaScript
  modules, which have multiple global namespaces.

The only goal is a little more safety.

<div id="toc">
</div>

## An Example

Library file.  Top level has `module`, `source`, `const`, and `proc`.

    # lib-foo.oil (no shebang line necessary)

    module lib-foo.oil || return 0  # module named after file
    source $_this_dir/lib-other

    const G_foo = {myvar: 42}

    proc foo-proc {
      echo 'hi from foo-proc'
    }

    # no main function

Executable file.  Top level the same 4, plus `oil-main` at the bottom.

    #!/usr/bin/env ysh

    # deploy.ysh: Deploy C++ program to a server
    module main || return 0  # executable programs use 'main' guard

    source $_this_dir/lib-foo.oil
    source $_this_dir/lib-bar.oil

    const DEST_HOST = 'example.com'
    const DEST_USER = 'homer'

    proc .private-p {
      echo "I don't want oil-main to find this"
    }

    proc _p {
      .private-p  # direct function call
      foo-proc
      echo hi
    }

    proc p {
      sudo $0 _p @ARGV  # argv dispatch pattern
    }

    oil-main  # dispatch to arguments in this module, except ones beginning with .

## Usage Guidelines

- Distinguish between `.oil` files that are executable programs, and those that
  are libraries
  - A `lib-` prefix or a `lib/` dir can make sense, but isn't required
- Every **file** needs a `module` guard
- Use `oil-main`
  - Optional "hide" symbols with `.`

Other:

- `source` must only be used at the top level.
- When using modules, it's considered bad style to put code at the top level.
  - Either ALL code is at the top level in short script, or NONE of it is.
  - See the [doc on variables](variables.html).

## Recap: Shell Has Separate Namespaces for Functions and Variables

TODO:

- Proc namespace 
- Var namespace (a stack)

The `source` just concatenates both.

This is like a Lisp 2.

Oil doesn't deviate from this!  It builds some things on top.

TODO: See Interpreter state / data model.

## Mechanisms

### Guarded Execution with `module`

- Use either `main` or `mylib.oil`

### `$_this_dir` For Imports Relative To the Current File

- This lets you move things around, version them, etc.

### The `oil-main` builtin dispatches to procs

The `$0` dispatch pattern.

### Shell Options `redefine_{proc,module}` Expose Name Conflicts

In batch mode, you'll get errors.

But you can iteratively test in interactive mode.

    source mymodule.oil  # 'module' guard will be bypassed in interactive mode

## Bundling 

### Oil Source Files

TODO / help wanted: Pea.

It's nice that we have this "sequential" or concatenative property of code!
Multiple "modules" can go in the same file.

Naming convention: `pkg-foo.oil` ?  I don't really think we should have
packages though? 

### With The Oil Interpreter

## Appendix: Related Documents

- Variables and Namespaces
- [QSN](qsn.html)
