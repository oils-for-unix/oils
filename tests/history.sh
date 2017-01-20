#!/bin/bash
#
# Usage:
#   ./history.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  echo hi
  # Does this work non interacitvely?  Nope.
  echo !$
  echo !!
}

"$@"
