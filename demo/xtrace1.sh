#!/bin/bash
#
# Usage:
#   ./xtrace1.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Problem:
# - There is no indentation for function calls
# - There is no indication of the function call.  It only traces simple
# commands.  'local' is also traced with the concrete value.

func() {
  local arg=$1
  echo "{ func $arg"
  echo "func $arg }"
}

main() {
  set -o xtrace

  echo '{ main'
  func main
  echo 'main }'

  # No indentation or increase in +
  ( func subshell)

  # Now we change to ++
  foo=$(func commandsub)
  echo $foo

  # Still +
  func pipeline | wc -l

  # Increase to three
  foo=$(echo $(func commandsub))
  echo $foo

  # Call it recursively
  $0 func dollar-zero

  # Call it recursively with 
  export SHELLOPTS
  $0 func dollar-zero-shellopts

  echo
  echo
  echo

  # OK this is useful.

  # https://unix.stackexchange.com/questions/355965/how-to-check-which-line-of-a-bash-script-is-being-executed
  PS4='+${LINENO}: '

  # Test runtime errors like this
  #PS4='+${LINENO}: $(( 1 / 0 ))'

  func ps4
  foo=$(func ps4-commandsub)
  echo foo
}

my-ps4() {
  for i in {1..3}; do
    echo -n $i
  done
}

# The problem with this is you don't want to fork the shell for every line!

call-func-in-ps4() {
  set -x
  PS4='[$(my-ps4)] '
  echo one
  echo two
}

"$@"
