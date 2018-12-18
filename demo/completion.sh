#!/bin/bash
#
# Demo of the bash completion API.
#
# Usage:
#   source demo/completion.sh

argv() {
  spec/bin/argv.py "$@"
}

complete_foo() {
  local first=$1
  local cur=$2
  local prev=$3

  echo
  argv args "$@"

  # NOTE: If you pass foo 'hi', then the words are quoted!  This is a mistake!
  # Also true for \hi and "hi".
  # If you pass foo $x, you get literally $x as a word!  It's BEFORE
  # evaluation rather than AFTER evaluation!
  #
  # This is asking the completion function to do something impossible!!!

  argv COMP_WORDS "${COMP_WORDS[@]}"
  argv COMP_CWORD "${COMP_CWORD}"

  # This value is used in main bash_completion script.

  argv source "${BASH_SOURCE[@]}"
  argv 'source[0]' "${BASH_SOURCE[0]}"

  # Test for prefix
  # bin is a dir
  for candidate in one two three bin; do
    if test "${candidate#$cur}" != "$candidate"; then
      COMPREPLY+=("$candidate")
    fi
  done
}

foo() {
  argv completed "$@"
}

complete_filedir() {
  local first=$1
  local cur=$2
  local prev=$3
  COMPREPLY=( $( compgen -d "$cur" ) )
}

complete_bug() {
  # Regression for issue where readline swallows SystemExit.
  comsub=$(echo comsub)

  COMPREPLY=(one two three $comsub)
}

complete_optdemo() {
  local first=$1
  local cur=$2
  local prev=$3

  # Dynamically set
  #compopt -o nospace

  # -o nospace doesn't work here, but it's accepted!
  COMPREPLY=( $( compgen -o nospace -d "$cur" ) )
}

# dirnames: add dirs if nothing matches
# plusdirs: always add dirs
# filenames: adds trailing slash if it is a directory
complete -F complete_foo -o dirnames -o filenames foo
complete -F complete_foo -o nospace foo2

# from _filedir
complete -F complete_filedir filedir

# isolated bug
complete -F complete_bug bug

# Test how the options work.  git uses nospace.
complete -F complete_optdemo -o nospace optdemo
