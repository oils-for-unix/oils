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
test-waitpid() { posix-test PosixTest.testWaitpid; }
test-write() { posix-test PosixTest.testWrite; }

# Conclusion: print CAN raise IOError with EINTR.
#
# It might be better to make our own functions:
#
# io.echo()  # print()
# io.log()   # print() to stderr

# NOTE: print() is a complicated function that ends up looking up
# sys.stdout.write().  So fixing write should fix print!
# But for simplicity, we could still get rid of print().  It's a complicated
# function with too many args.

test-print() { posix-test PosixTest.testPrint; }

# NOTES:
#
# - PEP 475 says that Python purposesly ignores EINTR on close() and dup2().
#   The reason is due to multi-threaded programs: close() and dup2() change
#   the descriptor table, so another thread could have reused the file
#   descriptor in that time!  This doesn't apply to the shell, so maybe we
#   should handle them?

# - The parts of fcntl() we use don't appear to return EINTR.  Not covered by
#   PEP 475.

"$@"
