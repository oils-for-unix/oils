OPy Compiler and Byterun
========================

The OPy compiler is a Python bytecode compiler written in Python.  See
[Building Oil with the OPy Bytecode Compiler][oil-with-opy].  It's currently
used to translate Python source code in Oil to `.pyc` files.

The `byterun/` directory is a fork of [byterun][].  It's an experiment for
learning what it will take to write a minimal interpreter for Oil.  It can
curretly run all the Oil unit tests, but isn't otherwise used.

[oil-with-opy]: http://www.oilshell.org/blog/2018/03/04.html

[byterun]: http://aosabook.org/en/500L/a-python-interpreter-written-in-python.html

Getting started
---------------

Start with https://github.com/oilshell/oil/wiki/Contributing .  This is
necessary to build the `py27.grammar` file and so forth.

Then:

    $ ./smoke.sh opy-hello2  # basic test of compiler and runtime

Compile Oil with the OPy compiler:

    $ ./build.sh oil-repo  # makes _tmp/osh-opy and _tmp/osh-ccompile

Run Oil unit tests, compiled with OPy, under CPython:

    $ ./test.sh oil-unit

Run Oil unit tests, compiled with OPy, under byterun (OPyPy):

    $ ./test.sh oil-unit-byterun   # Run Oil unit tests, compiled with OPy, under CPython


Another way I test it like this:

    $ testdata/regex_compile.py  # run with CPython
    $ ../bin/opyc run testdata/regex_compile.py

(TODO: these should be gold tests)


Demo: speed difference between OSH under CPython and OSH under byterun/OPyPy:

    ./demo.sh opypy-speed

TODO:

- Spec tests
  - ./test.sh spec all  # Some failures due to $0

OPy Compiler Regtest
--------------------

This uses golden data in `_regtest/`.

    ./regtest.sh compile  # note: different files than 'build.sh oil-repo'
    ./regtest.sh verify-golden

OPy Compiler Divergences from CPython
----------------------------

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

