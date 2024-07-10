#!/usr/bin/env bash
#
# Common shell functions for task scripts.
#
# Usage:
#   source devtools/run-task.sh
#    ...  # define task functions
#   run-task "$@"

# List all functions defined in this file (and not in sourced files).
_bash-print-funcs() {
  local funcs=($(compgen -A function))
  # extdebug makes `declare -F` print the file path, but, annoyingly, only
  # if you pass the function names as arguments.
  shopt -s extdebug
  declare -F "${funcs[@]}" | grep --fixed-strings " $0" | awk '{print $1}'
  shopt -u extdebug
}

_show-help() {
  # TODO:
  # - Use awk to find comments at the top of the file?
  # - Use OSH to extract docstrings

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

run-task() {
  if [[ $# -eq 0 || $1 =~ ^(--help|-h)$ ]]; then
    _show-help
    exit
  fi

  if ! declare -f "$1"; then
    echo "$0: '$1' isn't an action in this task file.  Try '$0 --help'"
    exit 1
  fi

  "$@"
}
