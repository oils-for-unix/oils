#!/usr/bin/env bash
#
# Usage:
#   oil_lang/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# TODO: Rename to ysh
OIL=${OIL:-'bin/oil'}

# This doesn't distinguish if they should parse with osh or Oil though!

parse-one() {
  set +o errexit
  $OSH -n "$@"
  if test $? -ne 0; then return 255; fi  # make xargs quit
}

test-parse-osh() {
  find oil_lang/testdata -name '*.sh' -o -name '*.osh' \
    | xargs -n 1 -- $0 parse-one
}

DISABLED-osh-cpp() {
  # We get buffer overflow here?
  local osh=_bin/cxx-asan/osh

  # Assertion failed
  #local osh=_bin/cxx-dbg/osh

  ninja $osh

  OSH=$osh test-parse-osh
}

test-run-osh() {
  ### Run programs with OSH

  for prog in oil_lang/testdata/*.{sh,osh}; do
    echo $prog

    local skip=''
    case $prog in
      (*/assign.osh) skip=T ;;
      (*/no-dynamic-scope.osh) skip=T ;;
      (*/inline-function-calls.sh) skip=T ;;
    esac

    if test -n "$skip"; then
      echo "skipping $prog"
      continue
    fi

    echo ---
    $OSH $prog
  done
}

test-run-oil() {
  ### Run programs with Oil / YSH

  for prog in oil_lang/testdata/*.oil; do
    echo ---
    $OIL $prog all
  done
}

demo() {
  ### Run some of them selectively

  bin/osh oil_lang/testdata/array-rewrite-1.sh

  bin/osh oil_lang/testdata/array-rewrite-2.sh
  bin/osh oil_lang/testdata/array-splice-demo.osh

  bin/osh oil_lang/testdata/hello.osh

  bin/osh oil_lang/testdata/inline-function-calls.oil all

  bin/osh oil_lang/testdata/sigil-pairs.sh

  set +o errexit
  # Fails correctly
  bin/osh oil_lang/testdata/no-dynamic-scope.osh

  bin/osh oil_lang/testdata/assign.osh
}

soil-run() {
  ### Used by soil/worker.sh.  Prints to stdout.
  run-test-funcs
}

run-for-release() {
  ### Used by devtools/release.sh.  Writes a file.
  run-other-suite-for-release oil-large run-test-funcs
}

"$@"
