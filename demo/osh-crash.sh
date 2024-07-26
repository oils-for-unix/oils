#!/usr/bin/env bash
#
# Usage:
#   ./osh-crash.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

g() {
  readonly g=1
  readonly -a bash_array=(a b)
  bash_array[5]=z

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
  OILS_CRASH_DUMP_DIR=_tmp bin/osh $0 main "$@"
}

_do-subshell() {
  echo PID=$$
  ( f a b c )
}

# Note: we get two difference crash dumps, with two different stacks.
#
# That's because we call through $0.

do-subshell() {
  # clear environment so it's smaller
  env -i OILS_CRASH_DUMP_DIR=_tmp \
    bin/osh $0 _do-subshell "$@"
}

_pipeline() {
  # All of these show multiple errors

  false | wc -l

  #{ echo 1; false; echo 2; } | wc -l

  #f() { echo 1; false; echo 2; }
  #f | tac
}

do-pipeline() {
  env -i PATH=$PATH OILS_CRASH_DUMP_DIR=_tmp \
    bin/osh $0 _pipeline
}

"$@"
