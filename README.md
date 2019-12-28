Oil Source Code
===============

[git-repo]: https://github.com/oilshell/oil

[![Build
Status](https://travis-ci.org/oilshell/oil.svg)](https://travis-ci.org/oilshell/oil)

[Oil][] is a new Unix shell.  It's our upgrade path from bash!  ([Why Create a
New Unix Shell?][why] / [2019 FAQ][faq])

Its [source code lives in git][git-repo].

[Oil]: https://www.oilshell.org/
[why]: https://www.oilshell.org/blog/2018/01/28.html
[faq]: https://www.oilshell.org/blog/2019/06/17.html

It's written in Python, but we deploy a native executable by reusing portions
of the [CPython](https://en.wikipedia.org/wiki/CPython) interpreter.

<div id="toc">
</div>

## Contributing

* Make sure to check out the [Contributing][] page.
* Let us know if you have problems getting started by posting on the `#oil-dev`
  channel of [oilshell.zulipchat.com][].
* Feel free to grab an [issue from
  Github](https://github.com/oilshell/oil/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
  Let us know what you're thinking before you get too far.

[Contributing]: https://github.com/oilshell/oil/wiki/Contributing
[oilshell.zulipchat.com]: https://oilshell.zulipchat.com/
[blog]: http://www.oilshell.org/blog/

### Quick Start on Linux

Fetch the source code:

    git clone https://github.com/oilshell/oil.git  # or your fork
    git submodule update --init --recursive        # to get dependencies

Build the Python extension, and run `bin/osh` (or `bin/oil`):

    bash$ build/dev.sh minimal
    ...
    # Now you should have a libc.so symlink in the repository root directory

    bash$ bin/osh
    osh$ name=world
    osh$ echo "hello $name"
    hello world

Try running a shell script you wrote with `bin/osh myscript.sh`.

This is called the **developer build**, and is **very different** from the
release tarball.  The [Contributing][] page describes this difference in
detail.

The release tarballs are linked from the [home
page](https://www.oilshell.org/).  (Developer builds don't work on OS X, so use
the release tarballs on OS X.)

Run `bin/oil` to try the Oil language.  Send me feedback about it!

### Docs

The [Wiki](https://github.com/oilshell/oil/wiki) has many developer docs.  Feel
free to edit them.  If you make a major change, let us know on Zulip!

There are also READMEs in some subdirs, like `opy/` and `mycpp/`.

If you're confused, the best thing to do is to ask on Zulip and someone should
produce a pointer and/or improve the docs.

Docs for **end users** are linked from each [release
page](https://www.oilshell.org/releases.html).

## Repository Structure

Try this to show a summary of what's in the repo and their line counts:

    $ metrics/source-code.sh all

(Other functions in this file may be useful as well.)

### A Collection of Interpreters

Oil is naturally structured as a set of mutually recursive parsers and
evaluators.

    bin/              # Main entry points (bin/osh)
    osh/              # OSH parser and evaluator
    oil_lang/         # Oil parser and evaluator
    frontend/         # Lexing/Parsing code common to Oil and OSH
    core/             # Other code shared between Oil and OSH
    pylib/            # Borrowed from the Python standard library.
    native/           # Python extension modules, e.g. libc.c
    cpp/              # C++ code which complements the mycpp translation
    tools/            # User-facing tools, e.g. the osh2oil translator
    Python-2.7.13/    # CPython is the initial basis for the Oil VM

### DSLs / Code Generators

Oil is implemented with DSLs and metaprogramming, for "leverage".

    asdl/             # ASDL implementation, derived from CPython
    pgen2/            # Parser Generator, borrowed from CPython
    mycpp/            # Experimental translator from typed Python to C++.
                      # Depends on MyPy.
    opy/              # Python compiler in Python (mycpp/ will replace it)
      lib/            # Common code
      compiler2/      # Bytecode compiler
      byterun/        # Metacircular bytecode VM in Python
      gold/           # tests
      byterun/        # Unused bytecode interpreter

### Several Kinds of Tests

Unit tests are named `foo_test.py` and live next to `foo.py`.

    test/             # Test automation
      unit.sh         ## Types of test runner: unit, spec, wild, smoke
      spec.sh
      wild.sh
      smoke.sh
      sh_spec.py      # shell spec test framework
    testdata/
    gold/             # Gold Test cases
    spec/             # Spec test cases
      bin/            # tools used in many spec tests
      testdata/       # scripts for specific test cases
      errors/         # TODO: migrate these bad shell scripts
    types/            # Scripts for running MyPy and PyAnnotate, etc.

### Dev Tools and Scripts

We use a lot of automation to improve the dev process.  It's largely written in
shell, of course!

    benchmarks/       # Benchmarks should be run on multiple machines.
    metrics/          # Metrics don't change between machines (e.g. code size)
    build/            # Build automation
      oil-defs/       # Files that define our slice of CPython.
      dev.sh          # For development builds, running CPython
    devtools/         # For Oil developers (not end users)
      release.sh      # The (large) release process.
    demo/             # Demonstrations of bash/shell features.  Could be
                      # moved to tests/ if automated.
    misc/             # A junk drawer
    web/              # HTML/JS/CSS for tests and tools
    lazylex/          # An HTML lexer which doctools/ builds upon.

### Temp Dirs

Directories that begin with `_` are **not** stored in `git`.  The dev tools
above create and use these dirs.

    _bin/             # Native executables are put here
    _build/           # Temporary build files
    _devbuild/        # Developer build files not deleted upon 'make clean'
      gen/            # Generated Python and C code
    _deps/            # build dependencies like re2c
    _tmp/             # Test suites and other temp files
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

### Build System for End Users

This is very different than the **developer build** of Oil.

    Makefile
    configure
    install

### Doc Sources

    doc/              # A mix of docs
    doctools/         # Tools that use lazylex/ to transform Markdown/HTML
    README.md         # This page, which is For Oil developers

    LICENSE.txt       # For end users
    INSTALL.txt

## More info

* [The blog][blog] has updates on the project status.
* [Oil Home Page](http://www.oilshell.org/)
* [oilshell.zulipchat.com][] is for any kind of discussion
* Subscribe for updates:
  * [/r/oilshell on Reddit](https://www.reddit.com/r/oilshell/)
  * [@oilshellblog on Twitter](https://twitter.com/oilshellblog)
