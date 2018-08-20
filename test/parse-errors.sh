#!/bin/bash
#
# Usage:
#   ./parse-errors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Run with SH=bash too
SH=${SH:-bin/osh}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_error-case() {
  banner "$@"
  echo
  $SH -c "$@"
}

cases-in-strings() {
  set +o errexit

  _error-case 'echo < <<'
  _error-case '${foo:}'
  _error-case '$(( 1 +  ))'
  _error-case 'echo $( echo > >>  )'
  _error-case 'echo ${'
}

# Cases in their own file
cases-in-files() {
  set +o errexit  # Don't fail

  for t in test/parse-errors/*.sh; do
    banner $t
    $SH $t
  done
}

all() {
  cases-in-strings

  echo
  echo ----------------------
  echo

  cases-in-files

  # Always passes
  return 0
}

# TODO: 
run-for-release() {
  local out=_tmp/parse-errors/log.txt
  mkdir -p $(dirname $out)

  echo '1'
  all >$out 2>&1
  echo "Wrote $out"
}

"$@"
