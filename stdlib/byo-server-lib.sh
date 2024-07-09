# Library to turn a file into a "BYO test server"
#
# Usage:
#   source --builtin test/byo-server-lib.sh   # from Oils
#   source test/byo-server-lib.sh             # can be used with bash
#
# The client creates a clean process state and directory state for each tests.
#
# (It relies on compgen -A, and maybe declare -f, so it's not POSIX shell.)

# TODO: How do I get stdlib/two.sh
log() {
  echo "$@" >& 2
}

die() {
  log "$0: fatal: $@"
  exit 1
}


byo-maybe-main() {
  local command=${BYO_COMMAND:-}

  case $command in
    '')
      # Do nothing if it's not specified
      return 
      ;;

    detect)
      # all the commands supported, except 'detect'
      echo list-tests
      echo run-test

      exit 66  # ASCII code for 'B' - what the protocol specifies
      ;;

    list-tests)
      # bash extension that OSH also implements
      compgen -A function | grep '^test-'
      exit 0
      ;;

    run-test)
      local test_name=${BYO_ARG:-}
      if test -z "$test_name"; then
        die "BYO run-test: Expected BYO_ARG"
      fi

      # Shell convention: we name functions test-*
      $test_name

      # Only run if not set -e.  Either way it's equivalent
      exit $?
      ;;

    *)
      die "Invalid BYO command '$command'"
      ;;
  esac

  # Do nothing if BYO_COMMAND is not set.
  # The program continues to its "main".
}
