#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

pgen2() {
  PYTHONPATH=. pgen2/pgen2_main.py "$@"
}

calc-test() {
  pgen2 parse pgen2/calc.grammar eval_input '1+2'
}

stdlib-test() {
  pgen2 stdlib-test
}

"$@"
