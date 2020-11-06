#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

tea-files() {
  find tea/testdata -name '*.tea' 
}

# TODO: We should have run --fail-with-status 255

parse-one() {
  set +o errexit

  # Standalone Tea parser.  Prints the CST.  TODO: Should print AST too?
  bin/tea -n "$@"
  if test $? -ne 0; then return 255; fi  # make xargs quit

  # Integrated Oil parser.  Prints AST.
  bin/oil -O parse_tea -n "$@"
  if test $? -ne 0; then return 255; fi  # make xargs quit
}

parse-all-tea() {
  # Parse with the Oil binary
  tea-files | xargs --verbose -n 1 -- $0 parse-one
}

usage-test() {
  local prog='data Point(x Int, y Int)'

  bin/oil -O parse_tea -n -c "echo 'hi'; $prog"

  bin/tea -n -c "$prog"
  #bin/tea -c "$prog"

  echo "$prog" | bin/tea -n
}

all() {
  parse-all-tea
  usage-test
}

travis() {
  ### Used by services/toil-worker.sh.  Prints to stdout.
  all
}

run-for-release() {
  ### Used by devtools/release.sh.  Writes a file.
  run-other-suite-for-release tea-large all
}

"$@"
