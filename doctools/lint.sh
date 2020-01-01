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

manifest() {
  find \
    _release/VERSION _tmp/unit _tmp/spec \
    -name '*.html' 
    # There are a lot of empty <pre></pre> here which I don't care about
    # _tmp/spec \
    #_tmp/test-opy _tmp/metrics \ 

  # TODO: include benchmarks.  Look at devtools/release.sh compress
}

all-html() {
  manifest | xargs -n 1 --verbose -- $0 validate-html
}

"$@"
