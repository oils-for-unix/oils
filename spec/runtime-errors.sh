#!/bin/bash
#
# Usage:
#   $SH ./runtime-errors.sh all
#
# Run with bash/dash/mksh/zsh.

#
# COMMAND ERRORS
#

no_such_command() {
  ZZZZZ

  echo 'SHOULD NOT GET HERE'
}

errexit() {
  set -o errexit
  false

  echo 'SHOULD NOT GET HERE'
}

pipefail() {
  false | wc -l

  set -o errexit
  set -o pipefail
  false | wc -l

  echo 'SHOULD NOT GET HERE'
}

# Other errors: permission denied for >, etc.
# Hm this is not fatal either.
nonexistent() {
  cat < nonexistent.txt

  echo 'SHOULD NOT GET HERE'
}

# NOTE: This prints a WARNING in bash.  Not fatal in any shell except zsh.
control_flow() {
  break
  continue

  echo 'SHOULD NOT GET HERE'
}

#
# WORD ERRORS
#

nounset() {
  set -o nounset
  echo $x

  echo 'SHOULD NOT GET HERE'
}

#
# ARITHMETIC ERRORS
#

divzero() {
  echo $(( 1 / 0 ))

  echo 'SHOULD NOT GET HERE'
}

#
# BOOLEAN ERRORS
#

# Only osh cares about this.
string_to_int() {
  [[ a -eq 0 ]]

  echo 'SHOULD NOT GET HERE'
}

#
# TEST DRIVER
#

_run_test() {
  local t=$1

  echo "--------"
  echo "    CASE: $t"
  # Run in subshell so the whole thing doesn't exit
  ( $t )
  echo "    STATUS: $?"
  echo
}

all() {
  # Can't be done inside a loop!
  _run_test control_flow 

  for t in \
    no_such_command errexit pipefail nonexistent nounset \
    divzero string_to_int; do

    _run_test $t
  done
}

"$@"
