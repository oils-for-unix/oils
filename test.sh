#!/bin/bash
#
# Run unit tests.
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Unit tests
#

export PYTHONPATH=.  # current dir

# For auto-complete
unit() {
  "$@"
}

all-unit() {
  local skip_c=${1:-}

  for t in {core,osh}/*_test.py; do
    if test -n "$skip_c" && [[ $t == *libc_test.py ]]; then
      continue
    fi
    echo $t
    $t
  done
}

"$@"
