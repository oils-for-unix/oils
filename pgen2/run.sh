#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

parse() {
  PYTHONPATH=. pgen2/pgen2_main.py parse "$@"
}

calc-test() {
  parse pgen2/calc.grammar eval_input '1+2'
}

"$@"
