#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   mycpp/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/common.sh
source cpp/NINJA-steps.sh
source mycpp/common.sh  # run-test

# in case binaries weren't built
shopt -s failglob

export ASAN_OPTIONS='detect_leaks=0'

examples-variant() {
  ### Run all examples using a variant

  local compiler=${1:-cxx}
  local variant=${2:-gcevery}
  local do_benchmark=${3:-}

  ninja mycpp-examples-$compiler-$variant

  set +o errexit

  local num_tests=0
  local num_failed=0
  local status=0

  local log_dir=_test/$compiler-$variant/mycpp/examples
  mkdir -p $log_dir

  for b in _bin/$compiler-$variant/mycpp/examples/*; do
    case $b in
      (*.stripped)  # just run the unstripped binary
        continue
        ;;
    esac

    local prefix="$log_dir/$(basename $b)"

    case $variant in
      (coverage)
        export LLVM_PROFILE_FILE=$prefix.profraw
        ;;
    esac

    local log="${prefix}${do_benchmark}.log"

    log "RUN $b > $log"

    local test_name=$(basename $b)
    if test -n "$do_benchmark" && [[ $test_name == test_* ]]; then
      log "Skipping $test_name in benchmark mode"
      continue
    fi

    BENCHMARK="$do_benchmark" $b >$log 2>&1

    status=$?

    if test "$status" -eq 0; then
      log 'OK'
    else
      log "FAIL with status $?"
      #return $status
    fi

    if test "$status" != 0; then
      num_failed=$((num_failed + 1))
    fi
    num_tests=$((num_tests + 1))
  done

  log ''
  log "$num_failed of $num_tests tests failed"
  log ''
}

#
# 3 Variants x {test, benchmark}
#

# 10 segfaults
ex-gcevery() {
  local compiler=${1:-}
  examples-variant "$compiler" gcevery
}

# TOO SLOW to run.  It's garbage collecting all the time.
ex-gcevery-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" gcevery '.BENCHMARK'
}

# PASS!
ex-asan() {
  local compiler=${1:-}
  examples-variant "$compiler" asan
}

# 2 of 18 tests failed: cartesian, parse
# So it does not catch the 10 segfaults that 'gcevery' catches with a few
# iterations!
ex-asan-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" asan '.BENCHMARK'
}

# PASS!  Under both clang and GCC.
ex-ubsan() {
  local compiler=${1:-}
  examples-variant "$compiler" ubsan
}

# same as ASAN: 2 of 18
ex-ubsan-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" ubsan '.BENCHMARK'
}

# PASS!
ex-opt() {
  local compiler=${1:-}
  examples-variant "$compiler" opt
}

# 2 of 18 tests failed
ex-opt-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" opt '.BENCHMARK'
}

#
# Unit Tests
#

unit() {
  ### Run by test/cpp-unit.sh

  local compiler=${1:-cxx}
  local variant=${2:-gcevery}

  log ''
  log "$0 unit $compiler $variant"
  log ''


  # TODO: Exclude examples here
  # ninja mycpp-$variant
  ninja mycpp-unit-$compiler-$variant

  local log_dir=_test/$compiler-$variant/mycpp
  mkdir -p $log_dir

  for b in _bin/$compiler-$variant/mycpp/*; do
    if ! test -f $b; then
      continue
    fi

    local prefix=$log_dir/$(basename $b)
    local log=$prefix.log

    log "RUN $b > $log"

    case $variant in
      (coverage)
        export LLVM_PROFILE_FILE=$prefix.profraw
        ;;
    esac

    set +o errexit
    $b >$log 2>&1
    local status=$?
    set -o errexit

    if test "$status" -eq 0; then
      log 'OK'
    else
      log "FAIL with status $?"
      return $status
    fi
  done
}

#
# Test failures
#

test-invalid-examples() {
  local mycpp=_bin/shwrap/mycpp_main
  ninja $mycpp
  for ex in mycpp/examples/invalid_*; do
    set +o errexit
    $mycpp '.:pyext' _tmp/mycpp-invalid $ex
    local status=$?
    set -o errexit

    if test $status -ne 1; then
      die "mycpp $ex: expected status 1, got $status"
    fi

  done

  log ''
  log "OK $0 mycpp test-invalid-examples"
}

soil-run() {
  test-invalid-examples

  # Run two tests that respect this variant
  unit '' oldstl

  # Run other unit tests, e.g. the GC tests
  unit '' asan
  unit '' ubsan
  unit '' gcstats
  unit '' gcevery
}

unit-test-coverage() {
  ### Invoked by Soil

  unit clang coverage

  local out_dir=_test/clang-coverage/mycpp
  test/coverage.sh html-report $out_dir mycpp
}

examples-coverage() {
  ### Invoked by Soil

  examples-variant clang coverage

  local out_dir=_test/clang-coverage/mycpp/examples
  test/coverage.sh html-report $out_dir mycpp/examples
}

"$@"
