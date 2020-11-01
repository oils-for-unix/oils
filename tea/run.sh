#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

tea-files() {
  find tea/testdata -name '*.tea' 
}

parse-all-tea() {
  # Parse with the Oil binary
  tea-files | xargs -n 1 -- bin/oil -O parse_tea -n

  # Standalone tea parser
  tea-files | xargs -n 1 -- bin/tea -n
}

usage-test() {
  local prog='data Point(x Int, y Int)'

  bin/oil -O parse_tea -n -c "echo 'hi'; $prog"

  bin/tea -n -c "$prog"
  #bin/tea -c "$prog"

  echo "$prog" | bin/tea -n
}

travis() {
  parse-all-tea
  usage-test
}

"$@"
