Oil Source Code
===============

[![Build
Status](https://github.com/oilshell/oil/actions/workflows/all-builds.yml/badge.svg)](https://github.com/oilshell/oil/actions/workflows/all-builds.yml) <a href="https://gitpod.io/from-referrer/">
  <img src="https://img.shields.io/badge/Contribute%20with-Gitpod-908a85?logo=gitpod" alt="Contribute with Gitpod" />
</a>



[Oil][] is a new Unix shell.  It's our upgrade path from bash to a better
language and runtime!  It's also for Python and JavaScript users who avoid
shell.  ([Why Create a New Unix Shell?][why])

[Oil]: https://www.oilshell.org/
[why]: https://www.oilshell.org/blog/2021/01/why-a-new-shell.html

It's written in Python, so the code is short and easy to change.  But we
automatically translate it to C++ with custom tools, to make it fast and small.
The deployed executable doesn't depend on Python.

This README is at the root of the [git repo][git-repo].

[git-repo]: https://github.com/oilshell/oil

<div id="toc">
</div>

## Contributing

* Try making the **dev build** of Oil with the instructions on the
  [Contributing][] page.  This should take 1 to 5 minutes if you have a Linux
  machine.
* If it doesn't, let us know.  You can post on the `#oil-dev` channel of
  [oilshell.zulipchat.com][], or file an issue on Github.
* Feel free to grab an [issue from
  Github](https://github.com/oilshell/oil/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
  Let us know what you're thinking before you get too far.

[Contributing]: https://github.com/oilshell/oil/wiki/Contributing
[oilshell.zulipchat.com]: https://oilshell.zulipchat.com/
[blog]: https://www.oilshell.org/blog/

### Quick Start on Linux

After following the instructions on the [Contributing][] page, you'll have a
Python program that you can quickly run and change!  Try it interactively:

    bash$ bin/osh

    osh$ name=world
    osh$ echo "hello $name"
    hello world

- Try running a shell script you wrote with `bin/osh myscript.sh`.
- Try the [Oil language](https://www.oilshell.org/cross-ref.html#oil-language)
  with `bin/oil`.

Let us know if any of these things don't work!  [The continuous
build](http://travis-ci.oilshell.org/) tests them at every commit.

### Dev Build vs. Release Build

Again, note that the **developer build** is **very different** from the release
tarball.  The [Contributing][] page describes this difference in detail.

The release tarballs are linked from the [home
page](https://www.oilshell.org/).  (Developer builds don't work on OS X, so use
the release tarballs on OS X.)

### Important: We Accept Small Contributions!

Oil is full of [many ideas](https://www.oilshell.org/blog/), which may be
intimidating at first.

But the bar to contribution is very low.  It's basically a medium size Python
program with many tests, and many programmers know how to change such programs.
It's great for prototyping.

- For OSH compatibility, I often merge **failing [spec
  tests](https://www.oilshell.org/cross-ref.html#spec-test)**.  You don't even
  have to write code!  The tests alone help.  I search for related tests with
  `grep xtrace spec/*.test.sh`, where `xtrace` is a shell feature.
- You only have to make your code work **in Python**.  Plain Python programs
  are easy to modify.  The semi-automated translation to C++ is a separate
  step, although it often just works. 
- You can **influence the design** of the Oil language.  If you have an itch to
  scratch, be ambitious.  For example, you might want to show us how to
  implement [nonlinear pipelines](https://github.com/oilshell/oil/issues/843).

### Docs

The [Wiki](https://github.com/oilshell/oil/wiki) has many developer docs.  Feel
free to edit them.  If you make a major change, let us know on Zulip!

There are also READMEs in some subdirectories, like `opy/` and `mycpp/`.

If you're confused, the best thing to do is to ask on Zulip and someone should
produce a pointer and/or improve the docs.

Docs for **end users** are linked from each [release
page](https://www.oilshell.org/releases.html).

## Repository Structure

Try this to show a summary of what's in the repo and their line counts:

    $ metrics/source-code.sh overview

(Other functions in this file may be useful as well.)

### A Collection of Interpreters

Oil is naturally structured as a set of mutually recursive parsers and
evaluators.  These interpreters are specified at a high-level: with regular
languages, Zephyr ASDL, and a statically-typed subset of Python.

    bin/              # Main entry points like bin/osh (source in bin/oils_for_unix.py)
    frontend/         # Input and lexing common to OSH and YSH
    osh/              # OSH parsers and evaluators (cmd, word, sh_expr)
    oil_lang/         # Oil parser and evaluator
    core/             # Other code shared between Oil and OSH
    pyext/            # Python extension modules, e.g. libc.c
    pylib/            # Borrowed from the Python standard library.
    qsn_/             # QSN serialization format
    tools/            # User-facing tools, e.g. the osh2oil translator

### DSLs / Code Generators

Here are the tools that transform that high-level code to efficient code:

    asdl/             # ASDL implementation, derived from CPython
    pgen2/            # Parser Generator, borrowed from CPython
    mycpp/            # Experimental translator from typed Python to C++.
                      # Depends on MyPy.  See mycpp/README.md
    pea/              # Perhaps a cleaner version of mycpp
    opy/              # Python compiler in Python (mycpp/ will replace it)

### Native Code and Build System

We have native code to support both the dev build (running under CPython) and
the oil-native build (pure C++):

    NINJA-config.sh   # Generates build.ninja

    build/            # High level build
      NINJA-steps.sh
      NINJA_main.py   # invoked by NINJA-config.sh
      NINJA_subgraph.py
      oil-defs/       # Files that define our slice of CPython.
      py.sh           # For development builds, running CPython
    cpp/              # C++ code which complements the mycpp translation
      NINJA-steps.sh
      NINJA_subgraph.py
    mycpp/            # Runtime for the translator
      NINJA-steps.sh
      NINJA_subgraph.py

    prebuilt/         # Prebuilt files committed to git, instead of in _gen/

    Python-2.7.13/    # For the slow Python build

    # Temp dirs (see below)
    _bin/
    _build/
    _gen/
    _test/

### Several Kinds of Tests

Unit tests are named `foo_test.py` and live next to `foo.py`.

    test/             # Test automation
      gold/           # Gold Test cases
      gold.sh         
      sh_spec.py      # shell spec test framework
      spec.sh         # Types of test runner: spec, unit, gold, wild
      unit.sh         
      wild.sh
    testdata/
    spec/             # Spec test cases
      bin/            # tools used in many spec tests
      testdata/       # scripts for specific test cases
      stateful/       # Tests that use pexpect

### Dev Tools and Scripts

We use a lot of automation to improve the dev process.  It's largely written in
shell, of course!

    benchmarks/       # Benchmarks should be run on multiple machines.
    metrics/          # Metrics don't change between machines (e.g. code size)
    client/           # Demonstration of OSH as a headless server.
    deps/             # Dev dependencies and Docker images
    devtools/         # For Oil developers (not end users)
      release.sh      # The (large) release process.
      services/       # talk to cloud services
    demo/             # Demonstrations of bash/shell features.  Could be
                      # moved to tests/ if automated.
      old/            # A junk drawer.
    web/              # HTML/JS/CSS for tests and tools
    soil/             # Multi-cloud continuous build (e.g. sourcehut, Github)

### Temp Dirs

Directories that begin with `_` are **not** stored in `git`.  The dev tools
above create and use these dirs.

    _bin/             # Native executables are put here
      cxx-dbg/
    _build/           # Temporary build files
    _cache/           # Dev dependency tarballs
    _devbuild/        # Generated Python code, etc.
    _gen/             # Generated C++ code that mirrors the repo
      frontend/
    _release/         # Source release tarballs are put here
      VERSION/        # Published at oilshell.org/release/$VERSION/
        benchmarks/
        doc/
        metrics/
        test/
          spec.wwz
          wild.wwz
          ...
        web/          # Static files, copy of $REPO_ROOT/web
          table/
    _test/            # Unit tests, mycpp examples
      tasks/
    _tmp/             # Output of other test suites; temp files
      spec/
      wild/
        raw/
        www/
      osh-parser/
      osh-runtime/
      vm-baseline/
      oheap/
      startup/
      ...

### Build Dependencies in `../oil_DEPS`

These tools are built from shell scripts in `soil/`.  The `oil_DEPS` dir is
"parallel" to Oil because it works better with container bind mounds.

    ../oil_DEPS/
      re2c/           # to build the lexer
      cmark/          # for building docs
      spec-bin/       # shells to run spec tests against
      mypy/           # MyPy repo
      mycpp-venv/     # MyPy binaries deps in a VirtualEnv

      py3/            # for mycpp and pea/
      cpython-full/   # for boostrapping Oil-CPython


### Build System for End Users version.

These files make the slow "Oil Python" build, which is very different than the
**developer build** of Oil.

    Makefile
    configure
    install

These files are for `oil-native` (in progress):

    _build/
      oil-native.sh

### Doc Sources

    doc/              # A mix of docs
    doctools/         # Tools that use lazylex/ to transform Markdown/HTML
    lazylex/          # An HTML lexer which doctools/ builds upon.
    README.md         # This page, which is For Oil developers

    LICENSE.txt       # For end users
    INSTALL.txt

## More info

* [The blog][blog] has updates on the project status.
* [Oil Home Page](https://www.oilshell.org/)
* [oilshell.zulipchat.com][] is for any kind of discussion
* Subscribe for updates:
  * [/r/oilshell on Reddit](https://www.reddit.com/r/oilshell/)
  * [@oilshellblog on Twitter](https://twitter.com/oilshellblog)


## Python Files Not Translated to C++

    mycpp/
      mylib.py  # statically typed equivalents of Python's data structures
    pylib/      # copied from Python stdlib
    core/
      py{error,os,util}.py  # too complicated to translate
    */*_def.py  # abstract definitions
    */*_gen.py  # code generators
