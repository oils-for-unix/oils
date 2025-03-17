spec/
====

Updated spec test format as of 2023-06.  Each file can have metadata at the
top.

## How to Run

Run individual files:

    test/spec-py.sh run-file smoke
    test/spec-cpp.sh run-file smoke

Run suites:

    test/spec-py.sh osh-all
    test/spec-py.sh ysh-all

    test/spec-cpp.sh osh-all
    test/spec-cpp.sh ysh-all

Faster way:

    NUM_SPEC_TASKS=2 test/spec-py.sh osh-all
    ...

## How to label


    ## suite: osh                   # REQUIRED: one of
                                    # {osh, ysh, tea, needs-terminal}
                                    # last one is not used

    ## tags: dev-minimal            # OPTIONAL: define a SUBSET of files to run
                                    # dev-minimal, interactive

    ## compare_shells: bash dash mksh  # for OSH, list of shells to compare against
                                       # empty for YSH

    ## our_shell: osh               # shell we run with
                                    # some ysh-* files run with osh

    ## oils_failures_allowed: 1     # number of failures we allow

## More Docs

- <https://github.com/oilshell/oil/wiki/Spec-Tests>
