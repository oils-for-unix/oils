#!/usr/bin/env bash
#
# Usage:
#   $SH ./runtime-errors.sh all
#
# Run with bash/dash/mksh/zsh.

#
# COMMAND ERRORS
#

no_such_command() {
  set -o errexit
  ZZZZZ

  echo 'SHOULD NOT GET HERE'
}

failed_command() {
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
# Hm this is not fatal unless set -o errexit.
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

nounset_arith() {
  set -o nounset
  echo $(( x ))

  echo 'SHOULD NOT GET HERE'
}

divzero() {
  echo $(( 1 / 0 ))

  echo 'SHOULD NOT GET HERE'
}

divzero_var() {
  local zero=0
  echo $(( 1 / zero ))

  echo 'SHOULD NOT GET HERE'
}

# Only dash flags this as an error.
string_to_int_arith() {
  local x='ZZZ'
  echo $(( x + 5 ))

  set -o strict-arith

  echo $(( x + 5 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_hex() {
  echo $(( 0xGG + 1 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_octal() {
  echo $(( 018 + 1 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_intbase() {
  echo $(( 16#GG ))

  echo 'SHOULD NOT GET HERE'
}

#
# BOOLEAN ERRORS
#

# Only osh cares about this.
string_to_int_bool() {
  [[ a -eq 0 ]]

  set -o strict-arith

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
    no_such_command failed_command pipefail nonexistent nounset \
    nounset_arith divzero divzero_var \
    string_to_int_arith string_to_hex string_to_octal \
    string_to_intbase string_to_int_bool; do

    _run_test $t
  done
}

"$@"
