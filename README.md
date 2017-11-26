Oil
===

Oil is a new Unix shell, still in its early stages.

This repo contains a bash-compatible shell called OSH, written in Python.

The dialect of bash that is recognized is called the [OSH
language][osh-language].  The main goal now is to design the [Oil
language][oil-language], which shell scripts can be automatically converted
to.

[osh-language]: http://www.oilshell.org/cross-ref.html#osh-language
[oil-language]: http://www.oilshell.org/cross-ref.html#oil-language

Oil is written in Python, but we deploy a native executable.  A subset of the
Python-2.7.13/ directory is packaged with the application.

Try it
------

Clone the repo, build the Python extension, and run `bin/osh`.  Basic things
like pipelines, variables, functions, etc. should work.

    bash$ build/dev.sh all
    ...
    # Now you should have a libc.so symlink in the repository root directory

    bash$ bin/osh
    osh$ name=world
    osh$ echo "hello $name"
    hello world

You can also try the [Oil 0.0
release](https://www.oilshell.org/blog/2017/07/23.html).

Contributing
------------

If you want to contribute, e-mail [oil-dev@oilshell.org][oil-dev].

[oil-dev]: http://lists.oilshell.org/listinfo.cgi/oil-dev-oilshell.org

[The blog](http://www.oilshell.org/blog/) has some general updates on the
project status.

For information on how to build and test Oil, see [Contributing][] on the wiki.

[Contributing]: https://github.com/oilshell/oil/wiki/Contributing

Code Overview
-------------

Try this to show a summary of what's in the repo and their line counts:

    $ scripts/count.sh all

(Other functions in this file may be useful as well.)

Directory Structure
-------------------

    # Development Scripts

    benchmarks/       # Test for speed
    build/            # Build automation
      dev.sh          # For development builds, running CPython
    test/             # Test automation
      unit.sh         ## Types of test runner: unit, spec, wild, smoke
      spec.sh
      wild.sh        
      smoke.sh
      sh_spec.py      # shell spec test framework
    spec/             # spec test cases
    scripts/          # Other development scripts
    web/              # HTML/JS/CSS for tests and tools

    # Oil Code

    Python-2.7.13/    # CPython is the initial basis for the Oil VM
    asdl/             # ASDL implementation
    bin/              # programs to run (bin/osh)
    core/             # the implementation (AST, runtime, etc.)
    native/           # Native code for Oil, e.g. libc.c
    osh/              # osh front end
    oil/              # oil front end (empty now)
    opy/              # Python compiler in Python
    tools/            # osh2oil translator

    # Temporary Directories

    _bin/             # Native executables are put here
    _build/           # Temporary build files
    _devbuild/        # Developer build files not deleted upon 'make clean'
    _deps/            # build dependencies like re2c
    _tmp/             # Temporary test files and the like
      spec/
      wild/
        raw/
        www/
      osh-parser/
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
      

    # Dev Docs

    README.md

    # End user docs

    LICENSE.txt
    INSTALL.txt

    # End user build system

    Makefile
    configure
    install

Unit tests are named `foo_test.py` and live next to `foo.py`.

More info
---------

Right now we're using
[/r/oilshell on Reddit](https://www.reddit.com/r/oilshell/) for general discussion.


I have docs that need to be cleaned up and published.  For now, there is a fair
amount of design information on
the [blog at oilshell.org](http://www.oilshell.org/blog/).

