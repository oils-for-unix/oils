spec/
====

2023-06 new style.

## How to Run

Run individual files:

    # TODO: change to spec-py.sh
    test/spec.sh run-file-with-metadata smoke

    test/spec-cpp.sh run-file-with-metadata smoke

Run suites:

    test/spec-py osh-all
    test/spec-py ysh-all

    test/spec-cpp.sh osh-all
    test/spec-cpp.sh ysh-all

## How to label


    suite: osh                      # REQUIRED: one of {osh, ysh, tea, needs-terminal}
                                    # last one is not used

    tags: dev-minimal               # OPTIONAL: defines a SUBSET of files to run
                                    # dev-minimal, needs-terminal

    compare_shells: bash dash mksh  # for OSH, list of shells to compare against
                                    # empty for YSH

    our_shell: osh                  # shell we run with
                                    # some ysh tests run with osh

    oils_allowed_failures: 1        # number of failures we can tolerate


## More Docs

- <https://github.com/oilshell/oil/wiki/Spec-Tests>
