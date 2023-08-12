---
default_highlighter: oil-sh
---

Hay - Custom Languages for Unix Systems
=======================================

*Hay* lets you use the syntax of the Oil shell to declare **data** and
interleaved **code**.  It allows the shell to better serve its role as
essential **glue**.  For example, these systems all combine Unix processes in
various ways:

- local build systems (Ninja, CMake, Debian package builds, Docker/OCI builds)
- remote build services (VM-based continuous integration like sourcehut, Github
  Actions)
- local process supervisors (SysV init, systemd)
- remote process supervisors / cluster managers (Slurm, Kubernetes)

Slogans:

- *Hay Ain't YAML*.
  - It evaluates to [JSON][] + Shell Scripts.
- *We need a better **control plane** language for the cloud*.
- *Oil adds the missing declarative part to shell*.

This doc describes how to use Hay, with motivating examples.

As of 2022, this is a new feature of Oil, and **it needs user feedback**.
Nothing is set in stone, so you can influence the language and its features!


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
      url = 'https://python.org'

      TASK build {           # a child node, with Oil code
        ./configure
        make
      }
    }

This program evaluates to a JSON tree, which you can consume from programs in
any language, including Oil:

    { "type": "Package",
      "args": [ "cpython" ],
      "attrs": { "version": "3.9", "url": "https://python.org" },
      "children": [
         { "type": "TASK",
           "args": [ "build" ],
           "code_str": "  ./configure\n  make\n"
         }
      ]
    }

That is, a package manager can use the attributes to create a build
environment, then execute shell code within it.  This is a *staged evaluation
model*.

## Understanding Hay

A goal of Hay is to restore the **simplicity** of Unix to distributed systems.
It's all just **code and data**!

This means that it's a bit abstract, so here are a few ways of understanding
it.

### Analogies

The relation between Hay and Oil is like the relationship between these pairs
of languages:

- [YAML][] / [Go templates][], which are used in Helm config for Kubernetes.
  - YAML data specifies a **service**, and templates specify **variants**.
- Two common ways of building C and C++ code:
  - [Make]($xref:make) / [Autotools]($xref:autotools)
  - [Ninja]($xref:ninja) / [CMake][]
  - Make and Ninja specify a **build graph**, while autotools and CMake detect
    a **configured variant** with respect to your system.

Each of these is *70's-style macro programming* &mdash; a stringly-typed
language generating another stringly-typed language, with all the associated
problems.

In contrast, Hay and Oil are really the same language, with the same syntax,
and the same Python- and JavaScript-like dynamic **types**.  Hay is just Oil
that **builds up data** instead of executing commands.

(Counterpoint: Ninja is intended for code generation, and it makes sense for
Oil to generate simple languages.)


[Go templates]: https://pkg.go.dev/text/template
[CMake]: https://cmake.org

### Prior Art

See the [Survey of Config Languages]($wiki) on the wiki, which puts them in
these categories:

1. Languages for String Data
   - INI, XML, [YAML][], ...
1. Languages for Typed Data 
   - [JSON][], TOML, ...
1. Programmable String-ish Languages 
   - Go templates, CMake, autotools/m4, ...
1. Programmable Typed Data 
   - Nix expressions, Starlark, Cue, ...
1. Internal DSLs in General Purpose Languages
   - Hay, Guile Scheme for Guix, Ruby blocks, ...

Excerpts:

[YAML][] is a data format that is (surprisingly) the de-facto control plane
language for the cloud.  It's an approximate superset of [JSON][].

[UCL][] (universal config language) and [HCL][] (HashiCorp config language) are
influenced by the [Nginx][] config file syntax.  If you can read any of these
languages, you can read Hay.

[Nix][] has a [functional language][nix-lang] to configure Linux distros.  In
contrast, Hay is multi-paradigm and imperative.

[nix-lang]: https://nixos.wiki/wiki/Nix_Expression_Language

The [Starlark][] language is a dialect of Python used by the [Bazel][] build
system.  It uses imperative code to specify build graph variants, and you can
use this same pattern in Hay.  That is, if statements, for loops, and functions
are useful in Starlark and Hay.

[Ruby][]'s use of [first-class
blocks](http://radar.oreilly.com/2014/04/make-magic-with-ruby-dsls.html)
inspired Oil.  They're used in systems like Vagrant (VM dev environments) and
Rake (a build system).

In [Lisp][], code and data are expressed with the same syntax, and can be
interleaved.
[G-Expressions](https://guix.gnu.org/manual/en/html_node/G_002dExpressions.html)
in Guix use a *staged evaluation model*, like Hay.

[YAML]: $xref:YAML
[UCL]: https://github.com/vstakhov/libucl
[Nginx]: https://en.wikipedia.org/wiki/Nginx
[HCL]: https://github.com/hashicorp/hcl
[Nix]: $xref:nix

[Starlark]: https://github.com/bazelbuild/starlark
[Bazel]: https://bazel.build/

[Ruby]: https://www.ruby-lang.org/en/
[Lisp]: https://en.wikipedia.org/wiki/Lisp_(programming_language)


### Comparison

The biggest difference between Hay and [UCL][] / [HCL][] is that it's
**embedded in a shell**.  In other words, Hay languages are *internal DSLs*,
while those languages are *external*.

This means:

1. You can **interleave** shell code with Hay data.  We'll discuss the many
   uses of this below.
   - On the other hand, it's OK to configure simple systems with plain data
     like [JSON][].  Hay is for when that stops working!
1. Hay isn't a library you embed in another program.  Instead, you use
   Unix-style **process-based** composition.
   - For example, [HCL][] is written in Go, which may be hard to embed in a C
     or Rust program.
   - Note that a process is a good **security** boundary.  It can be
     additionally run in an OS container or VM.

<!--
   - Code on the **outside** of Hay blocks may use the ["staged programming" / "graph metaprogramming" pattern][build-ci-comments] mentioned above.
   - Code on the **inside** is *unevaluated*.  You can execute it in another
     context, like a remote machine, Linux container, or virtual machine.
-->

The sections below elaborate on these points.

[shell-pipelines]: https://www.oilshell.org/blog/2017/01/15.html

<!--
    - Oil has an imperative programming model.  It's a little like Starlark.
    - Guile / GNU Make.
    - Tensorflow.
-->


## Overview

Hay nodes have a regular structure:

- They start with a "command", which is called the **type**.
- They accept **string** arguments and **block** arguments.  There must be at
  least one argument.

### Two Kinds of Nodes, and Three Kinds of Evaluation

There are two kinds of node with this structure.

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
'3.9'`.  That is, you don't need keywords like `const` or `var`.

(3) In contrast to these two types of Hay nodes, Oil builtins that take a block
usually evaluate it eagerly:

    cd /tmp {  # run in a new directory
      echo $PWD
    }

Builtins are spelled with `lower` case letters, so `SHELL` and `Attr` nodes
won't be confused with them.

### Two Stages of Evaluation

So Hay is designed to be used with a *staged evaluation model*:

1. The first stage follows the rules above:
   - Tree of Hay nodes &rarr; [JSON]($xref) + Unevaluated shell.
   - You can use variables, conditionals, loops, and more.
2. Your app or system controls the second stage.  You can invoke Oil again to
   execute shell inside a VM, inside a Linux container, or on a remote machine.

These two stages conceptually different, but use the **same** syntax and
evaluator!  Again, the evaluator runs in a mode where it **builds up data**
rather than executing commands.

### Result Schema

Here's a description of the result of Hay evaluation (the first stage).

    # The source may be "cpython.hay"
    FileResult = (source Str, children List[NodeResult])

    NodeResult =
      # package cpython { version = '3.9' }
      Attr (type                Str,
            args                List[Str],
            attrs               Map[Str, Any],
            children            List[NodeResult])

      # TASK build { ./configure; make }
    | Shell(type                Str,
            args                List[Str],
            location_str        Str,
            location_start_line Int,
            code_str            Str)


Notes:

- Except for user-defined attributes, the result is statically typed.
- Shell nodes are always leaf nodes.
- Attr nodes may or may not be leaf nodes.

## Three Ways to Invoke Hay

### Inline Hay Has No Restrictions

You can put Hay blocks and normal shell code in the same file.  Retrieve the
result of Hay evaluation with the `_hay()` function.

    # myscript.oil

    hay define Rule

    Rule mylib.o {
      inputs = ['mylib.c']

      # not recommended, but allowed
      echo 'hi'
      ls /tmp/$(whoami)
    }

    echo 'bye'  # other shell code

    const result = _hay()
    json write (result)

In this case, there are no restrictions on the commands you can run.

### In Separate Files 

You can put hay definitions in their own file:

    # my-config.hay

    Rule mylib.o {
      inputs = ['mylib.c']
    }

    echo 'hi'  # allowed for debugging
    # ls /tmp/$(whoami) would fail due to restrictions on hay evaluation

In this case, you can use `echo` and `write`, but the interpreted is
**restricted** (see below).

Parse it with `parse_hay()`, and evaluate it with `eval_hay()`:

    # my-evaluator.oil

    hay define Rule  # node types for the file
    const h = parse_hay('build.hay')
    const result = eval_hay(h)

    json write (result)
    # =>
    # {
    #   "children": [
    #     { "type": "Rule",
    #       "args": ["mylib.o"],
    #       "attrs": {"inputs": ["mylib.c"]}
    #     }
    #   ]
    # }

### In A Block

Instead of creating separate files, you can also use the `hay eval` builtin: 

    hay define Rule

    hay eval :result {  # assign to the variable 'result'
      Rule mylib.o {
        inputs = ['mylib.c']
      }
    }

    json write (result)  # same as above

This is mainly for testing and demos.

## Security Model: Restricted != Sandboxed

The "restrictions" are **not** a security boundary!  (They could be, but we're
not making promises now.)

Even with `eval_hay()` and `hay eval`, the config file is evaluated in the
**same interpreter**.  But the following restrictions apply:

- External commands aren't allowed
- Builtins other than `echo` and `write` aren't allowed
  - For example, the `.hay` file can't invoke `shopt` to change global shell
    options
- A new stack frame is created, so the `.hay` file can't mutate your locals
  - However it can still mutate globals with `setglobal`!

In summary, Hay evaluation is restricted to prevent basic mistakes, but your
code isn't completely separate from the evaluated Hay file.

If you want to evaluate untrusted code, use a **separate process**, and run it
in a container or VM.

## Reference

Here is a list of all the mechanisms mentioned.

### Shell Builtins

- `hay`
  - `hay define` to define node types.
  - `hay pp` to pretty print the node types.
  - `hay reset` to delete both the node types **and** the current evaluation
    result.
  - `hay eval :result { ... }` to evaluate in restricted mode, and put the
    result in a variable.
- Implementation detail: the `haynode` builtin is run when types like
  `Package` and `TASK` are invoked.  That is, all node types are aliases for
  this same builtin.

### Functions

- `parse_hay()` parses a file, just as `bin/ysh` does.
- `eval_hay()` evaluates the parsed file in restricted mode, like `hay eval`.
- `_hay()` retrieves the current result
  - It's useful interactive debugging.
  - The name starts with `_` because it's a "register" mutated by the
    interpreter.

### Options

Hay is parsed and evaluated with option group `ysh:all`, which includes
`parse_proc` and `parse_equals`.

<!--

- The `parse_brace` and `parse_equals` options are what let us inside attribute nodes
- `_running_hay`

-->


## Usage: Interleaving Hay and Oil

Why would you want to interleave data and code?  One reason is to naturally
express variants of a configuration.  Here are some examples.

**Build variants**.  There are many variants of the Oil binary:

- `dbg` and `opt`. the compiler optimization level, and whether debug symbols
  are included.
- `asan` and `ubsan`.  Dynamic analysis with Clang sanitizers.
- `-D GC_EVERY_ALLOC`. Make a build that helps debug the garbage collector.

So the Ninja build graph to produce these binaries is **shaped** similarly, but
it **varies** with compiler and linker flags.

**Service variants**.  A common problem in distributed systems is how to
develop and debug services locally.

Do your service dependencies live in the cloud, or are they run locally?  What
about state?  Common variants:

- `local`. Part or all of the service runs locally, so you may pass flags like
  `--auth-service localhost:8001` to binaries.
- `staging`. A complete copy of the service, in a different cloud, with a
  different database.
- `prod`. The live instance running with user data.

Again, these collections of services are all **shaped** similarly, but the
flags **vary** based on where binaries are physically running.

---

This model can be referred to as ["graph metaprogramming" or "staged
programming"][build-ci-comments].  In Oil, it's done with dynamically typed
data like integers and dictionaries.  In contrast, systems like CMake and
autotools are more stringly typed.

[build-ci-comments]: https://www.oilshell.org/blog/2021/04/build-ci-comments.html

The following **examples** are meant to be "evocative"; they're not based on
real code.  Again, user feedback can improve them!

### Conditionals

Conditionals can go on the inside of a block:

    Service auth.example.com {    # node taking a block
      if (variant === 'local') {  # condition
        port = 8001
      } else {
        port = 80
      }
    }

Or on the outside:

    Service web {               # node
      root = '/home/www'
    }

    if (variant === 'local') {  # condition
      Service auth-local {      # node
        port = 8001
      }
    }


### Iteration

Iteration can also go on the inside of a block:

    Rule foo.o {   # node
      inputs = []  # populate with all .cc files except one

      # variables ending with _ are "hidden" from block evaluation
      for name_ in *.cc {
        if name_ !== 'skipped.cc' {
          _ append(inputs, name_)
        }
      }
    }

Or on the outside:

    for name_ in *.cc {                # loop
      Rule $(basename $name_ .cc).o {  # node
        inputs = [name_]
      }
    }


### Remove Duplication with `proc`

Procs can wrap blocks:

    proc myrule(name) {

      # needed for blocks to use variables higher on the stack
      shopt --set dynamic_scope {

        Rule dbg/$name.o {      # node
          inputs = ["$name.c"]
          flags = ['-O0']
        }

        Rule opt/$name.o {      # node
          inputs = ["$name.c"]
          flags = ['-O2']
        }
        
      }
    }

    myrule foo  # call proc
    myrule bar  # call proc

Or they can be invoked from within blocks:

    proc set-port(port_num, :out) {
      setref out = "localhost:$port_num"
    }

    Service foo {      # node
      set-port 80 :p1  # call proc
      set-port 81 :p2  # call proc
    }

## More Usage Patterns

### Using Oil for the Second Stage

The general pattern is:

    ./my-evaluator.oil my-config.hay | json read :result

The evaluator does the following:

1. Sets up the execution context with `hay define`
1. Parses `my-config.hay` with `parse_hay()`
1. Evaluates it with `eval_hay()`
1. Prints the result as JSON.

Then a separate Oil processes reads this JSON and executes application code.

TODO: Show code example.

### Using Python for the Second Stage

In Python, you would:

1. Use the `subprocess` module to invoke `./my-evaluator.oil my-config.hay`. 
2. Use the `json` module to parse the result.
3. Then execute application code using the data.

TODO: Show code example.

### Locating Errors in the Original `.hay` File

The Oil interpreter has 2 flags starting with `--location` that give you
control over error messages.

    oil --location-str 'foo.hay' --location-start-line 42 -- stage2.oil

Set them to the values of fields `location_str` and `location_start_line` in
the result of `SHELL` node evaluation.

### Debian `.d` Dirs

Debian has a pattern of splitting configuration into a **directory** of
concatenated files.  It's easier for shell scripts to add to a directory than
add to a file.

This can be done with an evaluator that simply enumerates all files:

    var results = []
    for path in myconfig.d/*.hay {
      const code = parse_hay(path)
      const result = eval(hay)
      _ append(results, result)
    }

    # Now iterate through results

### Parallel Loading

TODO: Example of using `xargs -P` to spawn processes with `parse_hay()` and
`eval_hay()`.  Then merge the JSON results.

## Style

### Attributes vs. Procs

Assigning attributes and invoking procs can look similar:

    Package grep {
      version = '1.0'  # An attribute?

      version 1.0  # or call proc 'version'?
    }

The first style is better for typed data like integers and dictionaries.  The
latter style isn't useful here, but it could be if `version 1.0` created
complex Hay nodes.

### Attributes vs. Flags

Hay nodes shouldn't take flags or `--`.  Flags are for key-value pairs, and
blocks are better for expressing such data.

No:

    Package --version 1.0 grep {
      license = 'GPL'
    }

Yes:

    Package grep {
      version = '1.0'
      license = 'GPL'
    }

### Dicts vs. Blocks

Superficially, dicts and blocks are similar:

    Package grep {
      mydict = {name: 'value'}  # a dict

      mynode foo {              # a node taking a block
        name = 'value'
      }
    }

Use dicts in cases where you don't know the names or types up front, like

    files = {'README.md': true, '__init__.py': false}

Use blocks when there's a **schema**.  Blocks are also different because:

- You can use `if` statements and `for` loops in them.
- You can call `TASK build; TASK test` within a block, creating multiple
  objects of the same type.
- Later: custom validation

### Oil vs. Shell

Hay files are parsed as Oil, not OSH.  That includes `SHELL` nodes:

    TASK build {
      cp @deps /tmp   # Oil splicing syntax
    }

If you want to use POSIX shell or bash, use two arguments, the second of which
is a multi-line string:

    TASK build '''
      cp "${deps[@]}" /tmp
    '''

The Oil style gives you *static parsing*, which catches some errors earlier.

## Future Work

- `hay proc` for arbitrary schema validation, including JSON schema
- Examples of running hay in a secure process / container, in various languages
- Sandboxing:
  - More find-grained rules?
  - "restricted" could come with a security guarantee.  I've avoided making
    such guarantees,  but I think it's possible as Oil matures.  The
    interpreter uses dependency inversion to isolate I/O.
- More location info, including the source file.

[Please send
feedback](https://github.com/oilshell/oil/wiki/Where-To-Send-Feedback) about
Hay.  It will inform and prioritize this work!  

## Links

- Blog posts tagged #[hay]($blog-tag).  Hay is a general mechanism, so it's
  useful to explain it with concrete examples.
- [Data Definition and Code Generation in Tcl](https://trs.jpl.nasa.gov/bitstream/handle/2014/7660/03-1728.pdf) (2003, PDF) 
  - Like Hay, it has the (Type, Name, Attributes) data model.
- <https://github.com/oilshell/oil/wiki/Config-Dialect>.  Design notes and related links on the wiki.
