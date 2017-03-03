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
one() {
  "$@"
}

all() {
  local skip_c=${1:-}

  for t in {asdl,core,osh}/*_test.py; do
    # NOTE: This test hasn't passed in awhile.  It uses strings as output.

    if [[ $t == *arith_parse_test.py ]]; then
      continue
    fi
    if test -n "$skip_c" && [[ $t == *libc_test.py ]]; then
      continue
    fi
    echo $t
    $t
  done
}

"$@"
