#!/bin/bash
#
# Usage:
#   ./export.sh <function name>

#set -o nounset
set -o pipefail
set -o errexit

f1() {
  local f1_str=f1_str
  local f1_exported=f1_exported

  export f1_exported

  echo -n 'in f1: '
  tests/printenv.py f1_exported

  f1_global=f1_global
  export f1_global

  # f1_exported gets CLEANED UP here.
}

f1

echo $f1_str
# This doesn't look in the environment?  Oh I guess it gets cleaned up at the
# end.

echo -n 'global: '
tests/printenv.py f1_exported
echo $f1_exported

f1_global=AAA  # mutate exported variable
echo $f1_global
tests/printenv.py f1_global

