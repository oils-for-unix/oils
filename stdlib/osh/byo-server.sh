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

# List all functions defined in this file (and not in sourced files).
_bash-print-funcs() {
  ### Print shell functions in this file that don't start with _ (bash reflection)

  local funcs
  funcs=($(compgen -A function))
  # extdebug makes `declare -F` print the file path, but, annoyingly, only
  # if you pass the function names as arguments.
  shopt -s extdebug
  declare -F "${funcs[@]}" | grep --fixed-strings " $0" | awk '{print $1}'
  shopt -u extdebug
}

_gawk-print-funcs() {
  ### Print shell functions in this file that don't start with _ (awk parsing)

  # Using gawk because it has match()
  # - doesn't start with _

  # space     = / ' '* /
  # shfunc    = / %begin
  #               <capture !['_' ' '] ![' ']*>
  #               '()' space '{' space
  #               %end /
  # docstring = / %begin
  #               space '###' ' '+
  #               <capture dot*>
  #               %end /
  gawk '
  match($0, /^([^_ ][^ ]*)\(\)[ ]*{[ ]*$/, m) {
    #print NR " shfunc " m[1]
    print m[1]
    #print m[0]
  }

  match($0, /^[ ]*###[ ]+(.*)$/, m) {
    print NR " docstring " m[1]
  }
' $0
}

_print-funcs() {
  _bash-print-funcs
  return

  # TODO: make gawk work, with docstrings
  if command -v gawk > /dev/null; then
    _gawk-print-funcs
  else
    _bash-print-funcs
  fi
}


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
      # TODO: use _bash-print-funcs?  This fixes the transitive test problem,
      # which happened in soil/web-remote-test.sh
      # But it should work with OSH, not just bash!  We need shopt -s extdebug
      compgen -A function | grep '^test-'
      exit 0
      ;;

    run-test)
      local test_name=${BYO_ARG:-}
      if test -z "$test_name"; then
        die "BYO run-test: Expected BYO_ARG"
      fi

      # Avoid issues polluting recursive calls!
      unset BYO_COMMAND BYO_ARG

      # Shell convention: we name functions test-*
      "$test_name"

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
