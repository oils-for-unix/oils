OPy Compiler
============

Getting started / smoke test:

    ./build.sh grammar
    ./run.sh parse-test
    ./run.sh compile-hello2  # prints hello world
    ./run.sh compile-hello3  # no __future__ print_function

Compiling Oil:

    ./smoke.sh compile-osh-tree   # makes _tmp/osh-opy and _tmp/osh-ccompile
    ./smoke.sh test-unit  # Run Oil unit tests

TODO:

Move important stuff to build.sh.  smoke.sh doesn't make sense.

Notes
-----

OSH tests don't run under byterun.  I probably don't care.

    ./smoke.sh test-osh-tree '' byterun
