#!/bin/bash
#
# Usage:
#   ./osh-crash.sh <function name>

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

_do-subshell() {
  echo PID=$$
  ( f a b c )
}

# Problem: we get two difference crash dumps, with two different stacks.
# It would be nice to unify these somehow.
#
# Could we add a URL to link related crash dumps?  Maybe do it with PPID?  If a
# subshell exits with 1, and we have OSH_CRASH_DUMP_DIR, then we know it should
# have exited?
#
# MaybeCollect is done on fatal errors in several places.  MaybeDump is done on
# ExecuteAndCatch.  Subshells raise SystemExit?

do-subshell() {
  # clear environment so it's smaller
  env -i OSH_CRASH_DUMP_DIR=_tmp bin/osh $0 _do-subshell "$@"
}

"$@"
