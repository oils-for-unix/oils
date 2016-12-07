oil
===

Oil is a new Unix shell, still in its early stages.

This repo contains a prototype in Python of a very complete bash parser, along
with a runtime that is less complete.

The dialect of bash that is recognized is called the **osh language**.  The
main goal now is to design the **oil language**, which shell scripts can be
automatically converted to.

After that, the Python dependency can be broken by porting it to C++.

Try it
------

Clone the repo and run `bin/osh`.  Basic things like pipelines, variables,
functions, etc. should work.

    bash$ bin/osh
    osh$ name=world
    osh$ echo "hello $name"
    hello world

Build it
--------

Python's builtin `glob` and `fnmatch` modules don't match libc in some cases
(e.g. character classes).  To fix that, build the `core/libc.c` wrapper:

    $ ./pybuild.sh libc

Now `bin/osh` will use libc's globbing.

Running Tests
-------------

There are three kinds of tests: unit tests, spec tests, and "wild tests".

Unit tests are in Python:

    $ ./test.sh all-unit
    $ ./test.sh unit osh/word_parse_test.py

(test.sh is a simple wrapper that sets `PYTHONPATH`)

Spec tests are written with the `sh_spec.py` framework:

    $ ./spec.sh setup
    $ ./spec.sh smoke   # or other actions

"Wild tests" test the parser against code in the wild.  We don't have any
golden data to compare against, but whether the parse succeeds or fails is
useful for shaking out bugs, sort of like a fuzz test.

    $ ./wild.sh this-repo

This will run the parser on shell scripts in this repo, and put the output in
`_tmp/wild/oil-parsed`, which you can view with a web browser.

Code Overview
-------------

Try this to show a summary of what's in the repo and their line counts:

    $ ./count.sh all

(Other functions in this file that may be useful as well.)

Directory Structure
-------------------

    bin/              # programs to run (bin/osh)
    core/             # the implementation (AST, runtime, etc.)
    osh/              # osh front end
    oil/              # oil front end (empty now)
    tests/            # spec tests

    pybuild.sh        # build support
    setup.py

    test.sh           # test scripts
    spec.sh
    wild.sh
    smoke.sh
    sh_spec.py        # shell test framework

    lint.sh           # static analysis
    typecheck.sh

    count.sh          # Get an overview of the repo

    _tmp/             # For test temp files

Unit tests are named `foo_test.py` and live next to `foo.py`.

More info
---------

If you need help using oil, or have general questions, e-mail
[oil-discuss@oilshell.org][oil-discuss].

[oil-discuss]: http://lists.oilshell.org/listinfo.cgi/oil-discuss-oilshell.org

If you want to contribute, e-mail [oil-dev@oilshell.org][oil-dev].

[oil-dev]: http://lists.oilshell.org/listinfo.cgi/oil-dev-oilshell.org

I have docs that need to be cleaned up and published.  For now, there is a fair
amount of design information on
the [blog at oilshell.org](http://www.oilshell.org/blog/).

