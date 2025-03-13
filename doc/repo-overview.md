Oils Repo Overview
==================

Try this to show a summary of what's in the repo and their line counts:

    $ metrics/source-code.sh overview

(Other functions in this file may be useful as well.)

<div id="toc">
</div>

## Executable Spec

### A Collection of Interpreters

Oils is naturally structured as a set of mutually recursive parsers and
evaluators.  These interpreters are specified at a high-level: with regular
languages, Zephyr ASDL, and a statically-typed subset of Python.

    bin/              # Main entry points like bin/osh (source in bin/oils_for_unix.py)
    frontend/         # Input and lexing common to OSH and YSH
    osh/              # OSH parsers and evaluators (cmd, word, sh_expr)
    ysh/              # YSH parser and evaluator
    data_lang/        # Languages based on JSON
    core/             # Other code shared between OSH and YSH
    builtin/          # Builtin commands and functions
    pyext/            # Python extension modules, e.g. libc.c
    pylib/            # Borrowed from the Python standard library.
    tools/            # User-facing tools, e.g. the osh2oil translator
    display/          # User interface

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
the `oils-for-unix` build (pure C++):

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

## Build System for End Users

These files make the slow "Oils Python" build, which is very different than the
**developer build** of Oils.

    Makefile
    configure
    install

These files are for the C++ `oils-for-unix` tarball:

    _build/
      oils.sh

## Dev Tools

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

### Scripts

We use a lot of automation to improve the dev process.  It's largely written in
shell, of course!

    benchmarks/       # Benchmarks should be run on multiple machines.
    metrics/          # Metrics don't change between machines (e.g. code size)
    client/           # Demonstration of OSH as a headless server.
    deps/             # Dev dependencies and Docker images
    devtools/         # For Oils developers (not end users)
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
"parallel" to Oils because it works better with container bind mounds.

    ../oil_DEPS/
      re2c/           # to build the lexer
      cmark/          # for building docs
      spec-bin/       # shells to run spec tests against
      mypy/           # MyPy repo
      mycpp-venv/     # MyPy binaries deps in a VirtualEnv

      py3/            # for mycpp and pea/
      cpython-full/   # for bootstrapping Oils-CPython

## Docs

    doc/              # A mix of docs
    doctools/         # Tools that use lazylex/ to transform Markdown/HTML
    lazylex/          # An HTML lexer which doctools/ builds upon.
    README.md         # This page, which is For Oils developers

    LICENSE.txt       # For end users
    INSTALL.txt


## Related

- [README.md](oils-repo/README.html).  If you want to modify Oils, start here.
  We welcome contributions!
