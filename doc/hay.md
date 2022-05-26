---
default_highlighter: oil-sh
in_progress: true
---

Hay - Domain-Specific Languages in Oil
=====================================

Slogans

- Hay Ain't YAML
  - although also Tcl, Lua, Python, Ruby
- It evaluates to JSON + Shell Scripts
- A mix of declarative and imperative
- DSLs, Config Files, and More
- For Dialects of Oil

Use case examples


<!-- cmark.py expands this -->
<div id="toc">
</div>

## Concepts and Conventions

- Attribute blocks look like `package cppunit { version = '1.0' }`
- Shell blocks have a type that is ALL CAPS, like `TASK build { ... }`

## Functions

- `parse_hay()`
- `eval_hay()`
- `_hay_result()`  -- mutated register
- `block_as_str()`
  - or `shell_block_str()`.  Takes an unevaluated node BACK to a string
  - uses arena

## Builtins

- `hay` builtin
  - `hay define`
  - `hay pp`
    - `hay pp defs`
    - `hay pp result`
- `haynode ` is "aliased" by other types

## Options

- `parse_equals` is very important
- `sandbox:all` ?

## Schema for Output

It's statically typed, except for attrs, which are controlled by the user.

    # Source file is "foo.py"
    HayFile = (source_file Str, nodes Node*)

    Node =
      # package cppunit { version = '1.0'; user bob }
      Attr (type Str,
            name Str,
            attrs Map[Str, Any],
            children List[Node])
      # TASK build { configure; make }
    | Shell(type Str,
            name Str,
            block Block)


- So Attr nodes may or may not be leaf nodes.
- Shell nodes are always leaf nodes.

## Conditionals, Iteration, Abstraction

- Graph programming
- Staged Programming

## Use Cases

See Wiki.

## Patterns / Style


### Attributes vs. Functions

Choose:

    user alice  # Only if the proc creates a RECORD

    user = 'alice'  # for plain attributes


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

### Debian `.d` Dirs

I think we can support `source with:


    shopt --set sandbox:all
    shopt --unset sandbox_source_builtin  # ?

### No Flags

Hay words shouldn't take flags or `--`.  Flags are for key-value pairs, and
that is already covered by blocks.


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
