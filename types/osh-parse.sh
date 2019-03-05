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
    | sort | tee _tmp/osh-parse-src.txt | xargs wc -l | sort -n
}

typecheck() {
  MYPYPATH=. PYTHONPATH=.  mypy --py2 "$@"
}

check-some() {
  local flags='--strict'
  flags='--no-implicit-optional --no-strict-optional'

  # Somehow MyPy crashes on all files?
  # It doesn't like __future__.py, but that's ok!
  # AssertionError: ImportedName(_collections.defaultdict)

  #egrep '_devbuild|bin|asdl|pylib|frontend|core|osh|oil_lang' _tmp/osh-parse-src.txt | tee _tmp/to-check.txt
  egrep -v 'vendor|__future__' _tmp/osh-parse-src.txt | tee _tmp/to-check.txt

  set -x
  cat _tmp/to-check.txt | xargs -- $0 typecheck $flags >_tmp/err.txt || true

  cat _tmp/err.txt
  wc -l _tmp/err.txt

  #echo ---
  #diff -u _tmp/osh-parse-src.txt _tmp/to-check.txt
}

"$@"
