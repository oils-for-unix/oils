---
default_highlighter: oil-sh
in_progress: true
---

Hay - Domain-Specific Languages in Oil
=====================================

Hay is a way of using the syntax of the Oil shell to declare **data** and
interleaved **code**.  Example:

    hay define Package/TASK  # declare a tree of Hay node types

    Package cpython {        # a node that contains data
      version = '3.9'

      TASK build {           # a child node that contains code
        ./configure
        make
      }
    }

This evaluates to a JSON tree, which you can consume from programs in any
language (including Oil):

    { "type": "Package",
      "args": [ "cpython" ],
      "attrs": { "version": "3.9" },
      "children": [
         { "type": "TASK",
           "args": [ "build" ],
           "code_str": "  ./configure\n  make\n"
         }
      ]
    }

Slogans:

- *Oil Adds the Missing Declarative Part to Shell*
  - It evaluates to JSON + Shell Scripts.
- *Hay Ain't YAML*

This describes how to use Hay, and gives motivating examples.

<!--
  - although also Tcl, Lua, Python, Ruby
- DSLs, Config Files, and More
- For Dialects of Oil

Use case examples
-->

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Use Cases

A common pattern in Unix and distributed systems is to mix data and shell code.

- init systems
  - sysvinit embedded metadata in the **filename**
  - Systemd
- build systems
  - Make
  - CMake
- Docker
- Cluster managers like Kubernetes
  - these are like a "distributed init"
- YAML: CI services run in containers / VMs.

See Wiki for more.

### Prior Art

- UCL is based on Nginx config.
  - Oil is roughly "puning"
- HCL and UCL are similar, and HCL is for configuring cloud services.
- Nix has its own language to configure Linux distros.
- YAML uses JSON as a subset.

The biggest difference are the ways to interleave **code** with data:

- Code on the **outside** of hay blocks: "Staged programming" /
  graph metaprogramming.
  - Oil has an imperative programming model.  It's a little like Starlark.
  - Guile / GNU Make.
  - Tensorflow.
- Code on the **inside**: unevaluated code that you can execute in **another
  context**, like on a remote machine, Linux container, or virtual machine.

## Overview of Features

### Two Kinds of Nodes

**Data**. Attribute blocks have a type that starts with a capital letter:

    Package cpython {
      version = '3.9'
    }`

**Code**. Shell blocks have a type that is ALL CAPS:

    TASK build {
      ./configure
      make
    }

### Bare Assignment

In Oil, you assign variables like this:

    const version = '3.9'

Hay attribute nodes are a **special case** where this syntax is allowed:

    Package cpython {
       version = '3.9'   # no 'const', only within the block!
    }

### Oil versus Shell

Hay files are parsed as Oil, not OSH.  That includes code nodes:

    TASK build {
      cp @deps /tmp   # Oil splicing syntax
    }

If you want to use shell, you can use two arguments, the second of which is a
multi-line string:

    TASK build '''
      cp "${deps[@]}" /tmp
    '''

## Three Ways to Use Hay

### Inline: Not Sandboxed

### Inline: Sandboxed with `hay eval { }`

### Separate File: Sandboxed with `parse_hay()` and `eval_hay()`

## Interleaving Hay and Oil

- Graph programming
- Staged Programming

### Conditionals

- YAML and Go templates.

### Iteration

### Abstraction with `proc`

## Security Model

### First Stage of Evaluation

- Best effort

### Second Stage of Evaluation

- Use it

## Reference

### Schema for Output

It's statically typed, except for attrs, which are controlled by the user.

    # Source file is "foo.py"
    HayFile = (source_file Str, nodes Node*)

    Node =
      # package cppunit { version = '1.0'; user bob }
      Data (type Str,
            args Str[],  # list of strings
            attrs Map[Str, Any],
            children List[Node])

      # TASK build { configure; make }
    | Code(type Str,
            args Str[],
            location_str Str,
            location_start_line Int,
            code_str Str)


Note that:

- Code nodes are always leaf nodes.
- Data nodes may or may not be leaf nodes.

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

## FAQ

### Why is there a top-level node type?

Because there's no TYPE and NAME on the file.


## Links

- Config Dialect on wiki -- see use cases
- Alternatives / Prior Art
  - Tcl   -- data definition and code generation in TCL has the NAME TYPE
    ATTRIBUTES "meta" schema.
    - compare with HTML which is TYPE ATTRIBUTES CHILDREN
  - Lua
  - Python
  - Ruby
  - YAML
  - Custom languages
