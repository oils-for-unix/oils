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
    pylib/            # Borrowed from the Python standard library.
    tools/            # User-facing tools, e.g. the osh2oil translator
    display/          # User interface

### DSLs / Code Generators

Here are the tools that transform that high-level code to efficient code:

    asdl/             # ASDL implementation, derived from CPython
    pgen2/            # Parser Generator, borrowed from CPython
    mycpp/            # Experimental translator from typed Python to C++.
                      # Depends on MyPy.  See mycpp/README.md
    pea/              # Experiment: a cleaner version of mycpp?
    opy/              # Obsolete Python compiler

## Multiple Build Systems

### Dev Build Runs Under CPython

The Oils interpreter can run under a regular Python interpreter!  This build is
**slow**.

    build/ 
      py.sh           # For development builds, running CPython
    pyext/            # Python extension modules, e.g. libc.c
    Python-2.7.13/    # For the slow Python build
    Makefile          # For the tarball

### Generate C++, and Build Native Code with a `ninja` Wrapper

We have native code to support the `oils-for-unix` build, which is pure C++.

We build it with a Bazel-like wrapper around `ninja`:

    NINJA-config.sh       # Generates build.ninja

    build/                # High level build
      ninja_main.py       # invoked by NINJA-config.sh
      ninja_lib.py        # build rules
      ninja-rules-cpp.sh
      ninja-rules-py.sh
    cpp/                  # C++ code which complements the mycpp translation
      NINJA_subgraph.py
    mycpp/                # Runtime for the translator
      NINJA_subgraph.py

    prebuilt/             # Prebuilt files committed to git, instead of in
                          # _gen/

    # Temp dirs (see below)
    _bin/
    _build/
    _gen/
    _test/

### End User Build System Has Few Dependencies

Distro maintainers or end users should build from the `oils-for-unix` tarball,
not the repo.  ([The Oils Repo Is Different From the Tarball
Releases](https://github.com/oils-for-unix/oils/wiki/The-Oils-Repo-Is-Different-From-the-Tarball-Releases).)

We ship these files in the tarball:

    configure
    _build/
      oils.sh  # generated shell script
    install

So instead of running `ninja`, end users run `_build/oils.sh`, which invokes
the same "actions" as `ninja`.  

This means they don't need to install `ninja` &mdash; they only need a C++
compiler and a shell.

### Build Dependencies

TODO: this section is out of date.  We now use "wedges" in `~/wedge`.

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
      startup/
      ...

## Docs

    doc/              # A mix of docs
    doctools/         # Tools that use lazylex/ to transform Markdown/HTML
    data_lang/        # doctools/ builds upon the "HTM8" subset in this dir
    README.md         # This page, which is For Oils developers

    LICENSE.txt       # For end users
    INSTALL.txt

## Related

- [README.md](oils-repo/README.html).  If you want to modify Oils, start here.
  We welcome contributions!
