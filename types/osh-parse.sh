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

readonly PY_DEPS='_tmp/osh-parse-deps.txt'
readonly OSH_PARSE_MANIFEST='types/osh-parse-manifest.txt'

deps() {
  local pythonpath='.:vendor'
  local out=_build/osh_parse
  mkdir -p $out
  build/actions.sh app-deps osh_parse "$pythonpath" bin.osh_parse

  ls -l $out

  #head -n 30 $out/*

  echo ---

  # Around 16K lines, after stripping down the 'typing' module.

  awk '
  $1 ~ /^.*\.py$/ { print $1 }
  ' $out/app-deps-cpython.txt \
    | grep -v __init__ | sort | tee $PY_DEPS | xargs wc -l | sort -n
}

egrep-deps() {
  cat $PY_DEPS | xargs -- egrep "$@"
}

typecheck() {
  MYPYPATH=. PYTHONPATH=.  mypy --py2 "$@"
}

typecheck-all() {
  local manifest=$1
  local strict_none=${2:-}

  # 150 errors left without those flags.  But it doesn't impede translating to
  # C++ since you have nullptr.  Although List[Optional[int]] may be an issue.
  #local flags=''
  local flags
  if test -n "$strict_none"; then
    flags='--strict'
  else
    flags="--strict --no-implicit-optional --no-strict-optional"
  fi

  set +o errexit
  cat $manifest | xargs -- $0 typecheck $flags >_tmp/err.txt
  #echo "status: $?"

  echo
  cat _tmp/err.txt
  echo

  local num_errors=$(wc -l < _tmp/err.txt)

  # 1 type error allowed for asdl/pretty.py, because our --no-strict-optional
  # conflicts with demo/typed and so forth.
  if [[ $num_errors -eq 1 ]]; then
    return 0
  else
    echo "Expected 1 error, but got $num_errors"
    return 1
  fi

  #echo ---
  #diff -u _tmp/osh-parse-src.txt _tmp/to-check.txt
}

# The manifest needs to be checked in because we don't have
# _devbuild/cpython-full on Travis to crawl dependencies.
travis-setup() {
  deps
  egrep -v 'vendor|__future__' $PY_DEPS | tee $OSH_PARSE_MANIFEST
}

travis() {
  typecheck-all $OSH_PARSE_MANIFEST
}

"$@"
