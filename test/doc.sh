#!/bin/bash
#
# Usage:
#   ./doc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

validate-html() {
  # -e shows only errors
  # -q suppresses other text

  echo
  echo "--- $1"
  echo

  set +o errexit
  tidy -e -q -utf8 "$@"
  local status=$?

  if test $status -ne 0; then
    #exit 255  # stop xargs
    return $status
  fi
}

all-html() {
  find _release/VERSION -name '*.html' | xargs -n 1 --verbose -- $0 validate-html
}

"$@"
