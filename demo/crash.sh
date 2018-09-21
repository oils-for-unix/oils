#!/bin/bash
#
# Usage:
#   ./crash.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

g() {
  local g=1
  echo foo > $bar
}

f() {
  shift
  local flocal=flocal
  FOO=bar g A B
}

main() {
  f a b c
}

run-with-osh() {
  OSH_CRASH_DUMP_DIR=_tmp bin/osh $0 main "$@"
}

"$@"
