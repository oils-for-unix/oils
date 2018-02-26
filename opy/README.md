OPy Compiler
============

Getting started / smoke test:

    ./build.sh grammar
    ./run.sh parse-test
    ./run.sh compile-hello2  # prints hello world
    ./run.sh compile-hello3  # no __future__ print_function

Compiling Oil:

    ./build.sh oil-repo  # makes _tmp/osh-opy and _tmp/osh-ccompile

Testing:

    ./test.sh unit  # Run Oil unit tests

Test the binary:

    ./test.sh osh-help 
    ./test.sh osh-version 
    ./test.sh spec smoke
    ./test.sh spec all  # Failures due to $0

OPy Divergences from CPython
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

### Other

OSH tests don't run under byterun.  I probably don't care.

    ./test.sh unit '' byterun
