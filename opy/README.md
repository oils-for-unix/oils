OPy Compiler and Byterun
========================

The OPy compiler is a Python bytecode compiler written in Python.  See
[Building Oil with the OPy Bytecode Compiler][oil-with-opy].  It's currently
used to translate Python source code in Oil to `.pyc` files.

The `byterun/` directory is a fork of [byterun][].  It's an experiment for
learning what it will take to write a minimal interpreter for Oil.  It can
currently run all Oil unit tests, but isn't otherwise used.

[oil-with-opy]: http://www.oilshell.org/blog/2018/03/04.html

[byterun]: http://aosabook.org/en/500L/a-python-interpreter-written-in-python.html

## 2022 Update: OPy Will be "Replaced" By mycpp / Pea

A bytecode interpreter isn't fast enough to run Oil.  We still have the
double-interpretation problem.

## Getting started

Do the "Quick Start" in "in https://github.com/oilshell/oil/wiki/Contributing .

Then build the `py27.grammar` file:

    $ make _build/opy/py27.grammar.pickle

After Oil is setup, we can try out OPy.  Run these commands (and let me know if
any of them doesn't work):

    oil$ cd opy
    opy$ ../bin/opyc run gold/hello_py2.py  # basic test of compiler and runtime

Compile Oil with the OPy compiler:

    $ ./build.sh oil-repo  # makes _tmp/repo-with-opy and _tmp/repo-with-cpython

Run Oil unit tests, compiled with OPy, under **CPython**:

    $ ./test.sh oil-unit

Run Oil unit tests, compiled with OPy, under **byterun**:

    $ ./test.sh oil-unit-byterun   # Run Oil unit tests, compiled with OPy, under CPython

Gold tests in `gold/` compare the output of CPython vs. byterun:

    $ ./test.sh gold

Oil spec tests under byterun (slow):

    opy$ ./test.sh spec smoke  # like $REPO_ROOT/test/spec.sh smoke
    opy$ ./test.sh spec all    # like $REPO_ROOT/test/spec.sh all

FYI, they can be run manually like this:

    $ gold/regex_compile.py  # run with CPython
    $ ../bin/opyc run gold/regex_compile.py

Demo of the speed difference between OSH under CPython and OSH under byterun:

    ./demo.sh osh-byterun-speed

## OPy Compiler Regtest

This uses an old snapshot of the repo in `_regtest/`.

    ./regtest.sh compile
    ./regtest.sh verify-golden

## Notes on Three OPy Builds

- `$REPO_ROOT/_build/oil/bytecode-opy`: Bytecode for the release binary.  Built
  by `Makefile`.
- `$REPO_ROOT/opy/_tmp/repo-with-opy`: The entire repo with OPy.  For running
  Oil unit/spec tests under byterun, etc.  Built by `./build.sh oil-repo`.
- `$REPO_ROOT/opy/_tmp/regtest`: The snapshot of Python files in `opy/_regtest`
  are compiled, so we are insensitive to repo changes.  Built by `./regtest.sh
  compile`.
  
## OPy Compiler Divergences from CPython

### Lexer

- I don't remember where exactly, but I ran into a bug lexing the CPython test
  suite.  IIRC, CPython's lexer was more lenient about adjacent tokens without
  spaces than `tokenize.py`.
- `heapq.py` had `-*- coding: latin-1 -*-`, which causes problems.  OPy
  should require `utf-8` source anyway.

### Parser

- I ran into a bug where a file like `d = {}`, without a trailing newline,
  gives a parse error.  Adding the newline fixes it.
- print statements aren't allowed; we force Python 3-style `print(x, y,
  file=sys.stderr)`.  I think this is because the parser doesn't know about
  `__future__` statements, so it can't change the parsing mode on the fly.

### Bytecode Compiler

- I think there are no `LOAD_FAST` bytecodes generated?  TODO: Make a bytecode
  histogram using `opy/misc/inspect_pyc`.
- The OPy bytecode is bigger than the CPython bytecode!  Why is that?

