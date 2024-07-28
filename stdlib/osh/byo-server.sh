# Library to turn a shell file into a "BYO test server"
#
# Usage:
#
#   # from both bash and OSH
#   if test -z "$LIB_OSH"; then LIB_OSH=stdlib/osh; fi
#   source $LIB_OSH/byo-server-lib.sh
#
# The client creates a clean process state and directory state for each tests.
#
# (This file requires compgen -A, and maybe declare -f, so it's not POSIX
# shell.)

: ${LIB_OSH:-stdlib/osh}
source $LIB_OSH/two.sh

byo-maybe-run() {
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

byo-must-run() {
  local command=${BYO_COMMAND:-}
  if test -z "$command"; then
    die "Expected BYO_COMMAND= in environment"
  fi

  byo-maybe-run
}
