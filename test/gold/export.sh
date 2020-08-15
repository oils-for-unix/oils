#!/usr/bin/env bash
#
# Usage:
#   ./export.sh <function name>

#set -o nounset
set -o pipefail
set -o errexit

printenv() {
  spec/bin/printenv.py "$@"
}

f1() {
  local f1_str=f1_str
  local f1_exported=f1_exported

  export f1_exported

  echo -n 'in f1: '
  printenv f1_exported

  f1_global=f1_global
  export f1_global

  # f1_exported gets CLEANED UP here.
}

f1

echo $f1_str
# This doesn't look in the environment?  Oh I guess it gets cleaned up at the
# end.

echo -n 'global: '
printenv f1_exported
echo $f1_exported

f1_global=AAA  # mutate exported variable
echo $f1_global
printenv f1_global

# oil:setandexport
export E1=E1_VAL
printenv E1
unset E1
echo "E1: $E1"  # no longer set
printenv E1  # no longer exported

export E1=E1_VAL
export -n E1
echo "E1: $E1"  # Still set!  export and export -n aren't inverses.
printenv E1

echo ---

myexport() {
  # hm this is fully dynamic.  Not statically parseable!
  export "$@"
}
E3=E3_VAL
myexport E2=E2_VAL E3
echo "E2: $E2"
echo "E3: $E3"
printenv E2 E3
