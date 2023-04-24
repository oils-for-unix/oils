#!/usr/bin/env bash
#
# Common shell functions for task scripts.
#
# Usage:
#   source devtools/run-task.sh
#    ...  # define task functions
#   run-task "$@"

# List all functions defined in this file (and not in sourced files).
_list-funcs() {
  local funcs=($(compgen -A function))
  # extdebug makes `declare -F` print the file path, but, annoyingly, only
  # if you pass the function names as arguments.
  shopt -s extdebug
  declare -F "${funcs[@]}" | grep --fixed-strings " $0" | awk '{print $1}'
}

run-task() {
  if [[ $# -eq 0 || $1 =~ ^(--help|-h)$ ]]; then
    echo "Usage: $0 TASK_NAME ARGS..."
    echo
    echo "To complete tasks, run:"
    echo "   source devtools/completion.bash"
    echo
    echo "Tasks:"
    _list-funcs | column
    exit
  fi
  "$@"
}
