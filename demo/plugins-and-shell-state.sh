#!/bin/bash
#
# Investigation of https://github.com/oilshell/oil/issues/268
#
# Usage:
#   ./plugins-and-shell-state.sh <function name>



# Corrupts shell state in OSH.
#
# bash has save_parser_state and restore_parser_state, and bizarrely the exit
# code and pipe status are part of that!
#
# OK variables are protected because they're in a subshell.

PS1='$(echo ${MUTATED=hi }; echo $MUTATED; exit 42) $(echo $?)\$ '

foo() { argv foo "$@"; }
complete_foo() {
  local first=$1
  local cur=$2
  local prev=$3

  for candidate in one two three bin; do
    if [[ $candidate == $cur* ]]; then
      COMPREPLY+=("$candidate")
    fi
  done

  COMP_MUTATED='mutated by completion plugin'  # visible afterward

  return 23  # doesn't appear anywhere?
}
complete -F complete_foo foo
