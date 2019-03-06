#!/bin/bash
#
# Test of the standalone parser.
#
# Usage:
#   ./osh_parse.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  export PYTHONPATH=.
  echo 'echo hi' | bin/osh_parse.py "$@"
}

readonly PY_MANIFEST='_tmp/osh-parse-src.txt'

deps() {
  local pythonpath='.:vendor'
  local out=_build/osh_parse
  mkdir -p $out
  build/actions.sh app-deps osh_parse "$pythonpath" bin.osh_parse

  ls -l $out

  head -n 30 $out/*

  echo ---

  # Around 16K lines, after stripping down the 'typing' module.

  awk '
  $1 ~ /^.*\.py$/ { print $1 }
  ' $out/app-deps-cpython.txt \
    | sort | tee $PY_MANIFEST | xargs wc -l | sort -n
}

typecheck() {
  MYPYPATH=. PYTHONPATH=.  mypy --py2 "$@"
}

check-some() {
  local strict=${1:-}
  local flags='--no-implicit-optional --no-strict-optional'
  if test -n "$strict"; then
    flags="$flags --strict"
  fi

  egrep -v 'vendor|__future__' _tmp/osh-parse-src.txt | tee _tmp/to-check.txt

  set -x
  cat _tmp/to-check.txt | xargs -- $0 typecheck $flags >_tmp/err.txt || true

  cat _tmp/err.txt
  wc -l _tmp/err.txt

  #echo ---
  #diff -u _tmp/osh-parse-src.txt _tmp/to-check.txt
}

"$@"
