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

Notes
-----

OSH tests don't run under byterun.  I probably don't care.

    ./test.sh unit '' byterun
