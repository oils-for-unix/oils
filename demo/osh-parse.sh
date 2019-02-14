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

"$@"
