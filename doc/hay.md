---
default_highlighter: oil-sh
in_progress: true
---

Hay - Custom Languages for Unix Systems
=======================================

*Hay* lets you use the syntax of the Oil shell to declare **data** and
interleaved **code**.  It allows the shell to better serve its role as
essential **glue** between systems.  For example:

- local build systems (Ninja, CMake, Debian package builds, Docker/OCI builds)
- remote build services (VM-based continuous integration like sourcehut, Github
  Actions)
- local process supervisors (SysV init, systemd)
- remote process supervisors / cluster managers (Slurm, Kubernetes)

Slogans:

- *Hay Ain't YAML*. It evaluates to [JSON][] + Shell Scripts.
- *Oil Adds the Missing Declarative Part to Shell*

This doc describes how to use Hay, with motivating examples.

As of 2022, this is a new feature of Oil, and **it needs user feedback**.
Nothing is set in stone, so you can influence the language and feature set.


[JSON]: $xref:JSON

<!--
  - although also Tcl, Lua, Python, Ruby
- DSLs, Config Files, and More
- For Dialects of Oil

Use case examples
-->

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Example

Hay could be used to configure a hypothetical Linux package manager:

    # cpython.hay -- A package definition

    hay define Package/TASK  # define a tree of Hay node types

    Package cpython {        # a node with attributes, and children

      version = '3.9'
      home_page = 'https://python.org'

      TASK build {           # a child node, with Oil code
        ./configure
        make
      }
    }

This program evaluates to a JSON tree, which you can consume from programs in
any language, including Oil:

    { "type": "Package",
      "args": [ "cpython" ],
      "attrs": { "version": "3.9", "home_page": "https://python.org" },
      "children": [
         { "type": "TASK",
           "args": [ "build" ],
           "code_str": "  ./configure\n  make\n"
         }
      ]
    }


## Prior Art

A goal of Hay is to restore the **simplicity** of Unix to distributed systems.
It's all just **code and data**!

Here are some DSLs in the same area:

- [YAML][] is a data format that is (surprisingly) the de-facto control plane
  language for the cloud.  It's an approximate superset of [JSON][].
- [UCL][] (universal config language) is influenced by the [Nginx][] config
  file syntax.
- [HCL][] (HashiCorp config language) and [UCL][] are similar, and HCL is used
  to configure cloud services.
- [Nix][] has a functional language to configure Linux distros.  In contrast,
  Hay is multi-paradigm and imperative.
- The [Starlark][] language, used by the [Bazel][] build system, is a variant
  of Python.  The way it uses imperative code to specify variants of a graph
  influenced Hay.  That is, if statements, for loops, and functions are all
  idiomatic and useful in Starlark/Bazel.

And some general purpose languages:

- [Ruby][]'s use of [first-class
  "blocks"](http://radar.oreilly.com/2014/04/make-magic-with-ruby-dsls.html)
  inspired Oil.  They're used in systems like Vagrant (VM dev environments) and
  Rake (a build system).
- [Tcl](https://en.wikipedia.org/wiki/Tcl) commands can similarly be used to
  define data, although it's more "stringly typed" than Oil and JSON.

[YAML]: $xref:YAML
[UCL]: https://github.com/vstakhov/libucl
[Nginx]: https://en.wikipedia.org/wiki/Nginx
[HCL]: https://github.com/hashicorp/hcl
[Nix]: $xref:nix

[Starlark]: https://github.com/bazelbuild/starlark
[Bazel]: https://bazel.build/

[Ruby]: https://www.ruby-lang.org/en/


### Comparison

The biggest difference is that Hay is embedded in a shell, and uses the same
syntax.  This means:

1. It's not a parsing library you embed in another program.  Instead, you use
   Unix-style, polyglot process-based composition.
   - For example, [HCL][] is written in Go, which may be hard to embed in a
     Rust or C++ program.
2. You can interleave [multiparadigm shell code][shell-pipelines] with Hay
   data.
   - Code on the **outside** of Hay blocks may use a ["staged programming" / "graph metaprogramming" pattern][build-ci-comments].
   - Code on the **inside** is *unevaluated* code that you can execute in
     another context, like a remote machine, Linux container, or virtual
     machine.

The sections below elaborate on these points.

[shell-pipelines]: TODO
[build-ci-comments]: TODO

<!--
    - Oil has an imperative programming model.  It's a little like Starlark.
    - Guile / GNU Make.
    - Tensorflow.
-->


## Overview

### Two Kinds of Nodes, and Three Kinds of Evaluation

(1) `SHELL` nodes contain **unevaluated** code, and their type is ALL CAPS.
The code is turned into a string that can be executed elsewhere.

    TASK build {
      ./configure
      make
    }
    # =>
    # ... {"code_str": "  ./configure\n  make\n"}

(2) `Attr` nodes contain **data**, and their type starts with a capital letter.
They eagerly evaluate a block in a new **stack frame** and turn it into an
**attributes dict**.

    Package cpython {
      version = '3.9'
    }
    # =>
    # ... {"attrs": {"version": "3.9"}} ...

These blocks have a special rule to allow *bare assignments* like `version =
'3.9'`.  In contrast, Oil code requires keywords like `const` and `var`.

(3) In contrast to these two types of Hay nodes, Oil builtins that take a block
often evaluate it eagerly:

    cd /tmp {  # run in a new directory
      echo $PWD
    }

    fork {  # run in an async process
      sleep 3
    }

Builtins are spelled with lower case letters.

### Two Stages of Evaluation

So Hay is designed to be used with a "staged execution" model:

1. The first stage follows the rules above
   - A tree of Hay nodes &rarr; JSON + Unevaluated shell.
   - You can use variables, conditionals, loops, and more.
2. Your system controls the second stage.  You can invoke Oil again to execute
   shell inside a VM, inside a Linux container, or on a remote machine.

These two stages conceptually different, but use the same syntax and evaluator!
It's a form of metaprogramming.

### Output Schema

It's statically typed, except for attrs, which are controlled by the user.

    # The source may be "cpython.hay"
    FileResult = (source Str, children List[NodeResult])

    NodeResult =
      # package cpython { version = '3.9' }
      Attr (type Str,
            args List[Str],
            attrs Map[Str, Any],
            children List[NodeResult])

      # TASK build { ./configure; make }
    | Shell(type Str,
            args List[Str],
            location_str Str,
            location_start_line Int,
            code_str Str)


Note that:

- Code nodes are always leaf nodes.
- Data nodes may or may not be leaf nodes.


## Three Ways to Use It

### Inline Hay Has No Restrictions

You can execute commands in the middle.

### In Separate Files 

Restricted

Separate File: Sandboxed with `parse_hay()` and `eval_hay()`

### In A Block

Restricted

Inline: Sandboxed with `hay eval { }`


## Security Model: Restricted != Sandboxed

You can still mutate globals!  You need

1. First Stage has some isolation, but is "best effort".
   - You can execute this in a container.
2. Second stage often executes arbitrary code.  The shell uses the security
   model of the OS (e.g. the user it runs under.)


## Interleaving Hay and Oil

- Graph programming
- Staged Programming

### Conditionals

- YAML and Go templates.

### Iteration

### Abstraction with `proc`

## Reference


### Shell Builtins

- `hay` builtin
  - `hay define`
  - `hay pp` -- for debugging
  - `hay reset`
  - `hay eval { ... }`
- `haynode` builtin is "aliased" by other names: `Package` and `TASK`
  
### Functions

- `parse_hay()`
- `eval_hay()`
- `_hay()`  -- for interactive debugging

### Options

- `parse_brace` is very important
- `parse_equals` inside attribute nodes
- `_running_hay`
- `sandbox:all` ?



## Style

### Attributes vs. Procs

Choose:

    user alice  # Only if the proc creates a RECORD

    user = 'alice'  # for plain attributes


### Attributes vs. Flags

Hay words shouldn't take flags or `--`.  Flags are for key-value pairs, and
that is already covered by blocks.

### Dicts vs. Blocks

Superficially they are similar:

    mydict = {name: 'value'}

    myblock foo {  # blocks have names
       key = 'value'
    }

But they are different because blocks give you:

- Ability to instantiate multiple objects of a type
  - Later: with custom validation
- Metaprogramming: `if`, `for`, invoking procs, etc.

If you only want one object you can use a dict, like:

    package foo {
      resources = {
        cpu: 2,
        ram: 1 GB,
      }
    }

### Oil vs. Shell

Hay files are parsed as Oil, not OSH.  That includes SHELL nodes:

    TASK build {
      cp @deps /tmp   # Oil splicing syntax
    }

If you want to use POSIX shell or bash, use two arguments, the second of which
is a multi-line string:

    TASK build '''
      cp "${deps[@]}" /tmp
    '''

## Usage Patterns


### Using Oil for the Second Stage

### Using Python for the Second Stage

### Debian `.d` Dirs

I think we can support `source with:


    shopt --set sandbox:all
    shopt --unset sandbox_source_builtin  # ?

### Parallel Loading?

- I think you could use `xargs -P` to spawn processes with `parse_hay()` and
  `eval_hay()` and print JSON?
  - But

## Future Work

- `hay proc` for arbitrary schema validation, including JSON schema
- Example of running hay in a secure process / container, in various languages
- sandboxing:
  - more find-grained sandboxing
  - security guarantee?
  - I've avoided making any security guarantees.  But I think it's possible as
    Oil matures.  The code uses dependency inversion.
- More location info, and the source file

## Links

- Config Dialect on wiki -- see use cases
- Alternatives / Prior Art
  - Tcl   -- data definition and code generation in TCL has the NAME TYPE
    ATTRIBUTES "meta" schema.
    - compare with HTML which is TYPE ATTRIBUTES CHILDREN
