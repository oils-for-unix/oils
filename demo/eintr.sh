#!/bin/bash
#
# Test out our modifications to posixmodule.c to handle EINTR.
#
# Usage:
#   ./eintr.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

posix-test() {
  PYTHONPATH=.:vendor EINTR_TEST=1 \
    native/posix_test.py "$@"
}

test-read() { posix-test PosixTest.testRead; }
test-wait() { posix-test PosixTest.testWait; }
test-write() { posix-test PosixTest.testWrite; }

# Conclusion: print CAN raise IOError with EINTR.
#
# It might be better to make our own functions:
#
# io.echo()  # print()
# io.log()   # print() to stderr

test-print() { posix-test PosixTest.testPrint; }

"$@"
