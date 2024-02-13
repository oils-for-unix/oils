#!/usr/bin/env bash
#
# Usage:
#   ysh/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# TODO: Rename to ysh
OIL=${OIL:-'bin/oil'}
OSH_CPP=_bin/cxx-asan/osh
# Assertion failed
#OSH_CPP=_bin/cxx-dbg/osh

# This doesn't distinguish if they should parse with osh or ysh though!

parse-one() {
  echo ---
  # TODO: these tests can be removed once the rest of ysh/ is translated
  if test "$OSH" = "$OSH_CPP"; then
    local prog="$1"
    local skip=''
    case $prog in
      (*/assign.osh) skip=T ;;
    esac

    if test -n "$skip"; then
      echo "skipping $prog"
      return
    fi
  fi

  set +o errexit
  $OSH -n "$@"
  if test $? -ne 0; then return 255; fi  # make xargs quit
}

test-parse-osh() {
  find ysh/testdata -name '*.sh' -o -name '*.osh' \
    | xargs -n 1 -- $0 parse-one
}

test-run-osh() {
  ### Run programs with OSH

  for prog in ysh/testdata/*.{sh,osh}; do
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

test-run-ysh() {
  ### Run programs with YSH

  for prog in ysh/testdata/*.ysh; do
    echo ---
    $OIL $prog all
  done
}

demo() {
  ### Run some of them selectively

  bin/osh ysh/testdata/array-rewrite-1.sh

  bin/osh ysh/testdata/array-rewrite-2.sh
  bin/osh ysh/testdata/array-splice-demo.osh

  bin/osh ysh/testdata/hello.osh

  bin/osh ysh/testdata/inline-function-calls.ysh all

  bin/osh ysh/testdata/sigil-pairs.sh

  set +o errexit
  # Fails correctly
  bin/osh ysh/testdata/no-dynamic-scope.osh

  bin/osh ysh/testdata/assign.osh
}

soil-run() {
  ### Used by soil/worker.sh.  Prints to stdout.
  run-test-funcs
}

soil-run-cpp() {
  local osh=$OSH_CPP

  ninja $osh

  # TODO: replace with run-test-funcs once the rest of ysh is translated
  OILS_GC_ON_EXIT=1 OSH=$osh test-parse-osh
}

run-for-release() {
  ### Used by devtools/release.sh.  Writes a file.
  run-other-suite-for-release ysh-large run-test-funcs
}

"$@"
