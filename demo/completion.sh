#!/bin/bash
#
# Completion scripts
#
# Usage:
#   source demo/completion.sh <function name>

argv() {
  spec/bin/argv.py "$@"
}

complete_foo() {
  argv args "$@"

  argv COMP_WORDS "${COMP_WORDS[@]}"
  argv COMP_CWORD "${COMP_CWORD}"

  # This value is used in main bash_completion script.

  argv source "${BASH_SOURCE[@]}"
  argv 'source[0]' "${BASH_SOURCE[0]}"

  COMPREPLY=(one two three)
}

complete -F complete_foo foo

