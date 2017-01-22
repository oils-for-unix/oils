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

  # Hm this doesn't work either?  It's only for turning OFF in interactive
  # shells maybe?
  set -o histexpand

  echo hi
  echo !$
  echo !!
}

"$@"
