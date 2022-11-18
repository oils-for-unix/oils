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
source build/ninja-rules-cpp.sh
source devtools/common.sh
source soil/common.sh  # find-dir-html
source test/common.sh  # run-test-bin

# in case binaries weren't built
shopt -s failglob

# Will be needed to pass ASAN leak detector?  Or only do this for the main binary?
# export OIL_GC_ON_EXIT=1

examples-variant() {
  ### Run all examples using a variant -- STATS only

  local compiler=${1:-cxx}
  local variant=${2:-gcevery}
  local do_benchmark=${3:-}

  banner "$0 examples-variant $compiler $variant"

  ninja mycpp-examples-$compiler-$variant

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

    set +o errexit
    BENCHMARK="$do_benchmark" $b >$log 2>&1
    status=$?
    set -o errexit

    if test "$status" -eq 0; then
      log 'OK'
    else
      log "FAIL with status $?"
      log ''
      #return $status
      num_failed=$((num_failed + 1))
    fi

    num_tests=$((num_tests + 1))
  done

  log ''
  log "$num_failed of $num_tests tests failed"
  log ''

  case $variant in
    (gcevery)
      if test $num_failed -ne 5; then
        # echo "FAIL: Expected 5 failures with GC_EVERY_ALLOC"
        return 0  # not an error with -D RET_VAL_ROOTING
      fi
      ;;
    (*)
      if test $num_failed -ne 0; then
        echo "FAIL: Expected no failures, got $num_failed"
        return 1
      fi
      ;;
  esac

  return 0
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

  ninja mycpp-unit-$compiler-$variant

  local -a binaries=(_bin/$compiler-$variant/mycpp/*)

  # Add these files if they exist in the variant
  if test -d _bin/$compiler-$variant/mycpp/demo; then
    binaries+=(_bin/$compiler-$variant/mycpp/demo/*)
  fi

  local asan_options=''

  for b in "${binaries[@]}"; do
    if ! test -f $b; then
      continue
    fi

    local prefix=${b//_bin/_test/}
    local log=$prefix.log
    mkdir -p $(dirname $log)

    case $b in
      # leaks with malloc
      (*/demo/hash_table|*/demo/target_lang)
        asan_options='detect_leaks=0'
        ;;

      # What is the problem here?  300 allocations leaked.
      (*/gc_mylib_test)
        asan_options='detect_leaks=0'
        ;;
    esac

    ASAN_OPTIONS=$asan_options run-test-bin $b
  done
}

#
# Test failures
#

test-invalid-examples() {
  local mycpp=_bin/shwrap/mycpp_main
  ninja $mycpp
  for ex in mycpp/examples/invalid_*; do

    banner "$ex"

    set +o errexit
    $mycpp '.:pyext' _tmp/mycpp-invalid $ex
    local status=$?
    set -o errexit

    if test $status -ne 1; then
      die "mycpp $ex: expected status 1, got $status"
    fi

  done
}

test-runtime() {
  # Run other unit tests, e.g. the GC tests

  # Special test

  local bin=_bin/cxx-asan-D_BUMP_LEAK/mycpp/bump_leak_heap_test
  ninja $bin
  run-test-bin $bin

  local bin=_bin/cxx-ubsan-D_BUMP_LEAK/mycpp/bump_leak_heap_test
  ninja $bin
  run-test-bin $bin

  # Run other tests with all variants

  unit '' ubsan

  unit '' asan
  unit '' gcverbose
  unit '' gcevery
  # unit '' rvroot
}

#
# Translator
#

test-translator() {
  ### Invoked by soil/worker.sh

  # examples-variant '' rvroot

  examples-variant '' asan

  # Test with more collections -- 5 failures above
  examples-variant '' gcevery

  run-test-func test-invalid-examples _test/mycpp/test-invalid-examples.log

  # Runs test in cxx-asan variant, and benchmarks in cxx-opt variant
  if ! ninja mycpp-logs-equal; then
    log 'FAIL mycpp-logs-equal'
    return 1
  fi
}

unit-test-coverage() {
  ### Invoked by Soil

  unit clang coverage

  local out_dir=_test/clang-coverage/mycpp
  test/coverage.sh html-report $out_dir clang-coverage/mycpp
}

examples-coverage() {
  ### Invoked by Soil

  examples-variant clang coverage

  local out_dir=_test/clang-coverage/mycpp/examples
  test/coverage.sh html-report $out_dir clang-coverage/mycpp/examples
}

compare-malloc-leak-parse() {
  ninja _bin/cxx-{opt,mallocleak}/osh_eval

  for bin in _bin/cxx-{opt,mallocleak}/osh_eval; do
    echo $bin
    time $bin --ast-format none -n benchmarks/testdata/configure-coreutils
  done
}

compare-malloc-leak-example() {
  local example=${1:-escape}
  ninja _bin/cxx-{opt,mallocleak}/mycpp/examples/$example.mycpp
  for bin in _bin/cxx-{opt,mallocleak}/mycpp/examples/$example.mycpp; do
    echo $bin
    time BENCHMARK=1 $bin
    # time BENCHMARK=1 gdb --args $bin
  done

  echo PYTHON
  time PYTHONPATH=.:vendor BENCHMARK=1 mycpp/examples/$example.py
}

# Call function $1 with arguments $2 $3 $4
#
# mycpp/TEST.sh examples-variant '' asan

"$@"
