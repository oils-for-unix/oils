# Library to turn a file into a "BYO test server"
#
# Usage:
#   source --builtin test/byo-server-lib.sh   # from Oils
#   source test/byo-server-lib.sh             # can be used with bash
#
# The client creates a clean process state and directory state for each tests.
#
# (It relies on compgen -A, and maybe declare -f, so it's not POSIX shell.)

byo-maybe-main() {
  if test -n "${BYO_LIST_TESTS:-}"; then
    # bash extension that OSH also implements
    compgen -A function | grep '^test-'
    exit 0
  fi

  local test_name=${BYO_TEST_NAME:-}
  if test -n "$test_name"; then
    # Shell convention: we name functions test-*
    $test_name

    # Only run if not set -e.  Either way it's equivalent
    exit $?
  fi

  # Do nothing if none of those variables is set.
  # The program continues to its "main".
}
