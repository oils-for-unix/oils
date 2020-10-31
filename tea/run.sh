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
  tea-files | xargs -n 1 -- bin/tea
}

travis() {
  parse-all-tea
}

"$@"
