#!/usr/bin/env bash
#
# Common shell functions for task scripts.
#
# Usage:
#   source $LIB_OSH/task-five.sh
#
#   test-foo() {  # define task functions
#     echo foo
#   }
#   task-five "$@"

# Definition of a "task"
#
# - File invokes task-five "$@"
#   - or maybe you can look at its source
# - It's a shell function
#   - Has ### docstring
#   - Doesn't start with _

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/byo-server.sh


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

_awk-print-funcs() {
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
  awk '
  match($0, /^([^_ ][^ ]*)\(\)[ ]*{[ ]*$/, m) {
    print NR " shfunc " m[1]
    #print m[0]
  }

  match($0, /^[ ]*###[ ]+(.*)$/, m) {
    print NR " docstring " m[1]
  }
' $0
}

_show-help() {
  # TODO:
  # - Use awk to find comments at the top of the file?
  # - Use OSH to extract docstrings
  # - BYO_COMMAND=list-tasks will reuse that logic?  It only applies to the
  #   current file, not anything in a different file?

  echo "Usage: $0 TASK_NAME ARGS..."
  echo
  echo "To complete tasks, run:"
  echo "   source devtools/completion.bash"
  echo
  echo "Tasks:"

  if command -v column >/dev/null; then
    _bash-print-funcs | column
  else
    _bash-print-funcs
  fi
}

task-five() {
  # Respond to BYO_COMMAND=list-tasks, etc.  All task files need this.
  byo-maybe-run

  case ${1:-} in
    ''|--help|-h)
      _show-help
      exit 0
      ;;
  esac

  if ! declare -f "$1" >/dev/null; then
    echo "$0: '$1' isn't an action in this task file.  Try '$0 --help'"
    exit 1
  fi

  "$@"
}
