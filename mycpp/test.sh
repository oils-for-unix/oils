#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   mycpp/test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# in case binaries weren't built
shopt -s failglob

export ASAN_OPTIONS='detect_leaks=0'

examples-variant() {
  ### Run all examples using a variant

  local compiler=${1:-cxx}
  local variant=${2:-testgc}
  local do_benchmark=${3:-}

  ninja mycpp-examples-$compiler-$variant

  set +o errexit

  local num_tests=0
  local num_failed=0
  local status=0

  local log_dir=_test/$compiler-$variant/mycpp-examples
  mkdir -p $log_dir

  for b in _bin/$compiler-$variant/mycpp-examples/*; do
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

    echo "RUN $b > $log"

    local test_name=$(basename $b)
    if test -n "$do_benchmark" && [[ $test_name == test_* ]]; then
      echo "Skipping $test_name in benchmark mode"
      continue
    fi

    BENCHMARK="$do_benchmark" $b >$log 2>&1

    status=$?

    if test "$status" -eq 0; then
      echo 'OK'
    else
      echo "FAIL with status $?"
      #return $status
    fi

    if test "$status" != 0; then
      num_failed=$((num_failed + 1))
    fi
    num_tests=$((num_tests + 1))
  done

  echo
  echo "$num_failed of $num_tests tests failed"
  echo
}

#
# 3 Variants x {test, benchmark}
#

# 10 segfaults
ex-testgc() {
  local compiler=${1:-}
  examples-variant "$compiler" testgc
}

# TOO SLOW to run.  It's garbage collecting all the time.
ex-testgc-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" testgc '.BENCHMARK'
}

# PASS!
ex-asan() {
  local compiler=${1:-}
  examples-variant "$compiler" asan
}

# 2 of 18 tests failed: cartesian, parse
# So it does not catch the 10 segfaults that 'testgc' catches with a few
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
  local variant=${2:-testgc}

  echo
  echo "mycpp/test.sh unit $compiler $variant"
  echo


  # TODO: Exclude examples here
  # ninja mycpp-$variant
  ninja mycpp-unit-$compiler-$variant

  local log_dir=_test/$compiler-$variant/mycpp-unit
  mkdir -p $log_dir

  for b in _bin/$compiler-$variant/mycpp-unit/*; do
    local prefix=$log_dir/$(basename $b)
    local log=$prefix.log

    echo "RUN $b > $log"

    case $variant in
      (coverage)
        export LLVM_PROFILE_FILE=$prefix.profraw
        ;;
    esac

    # I believe gc_heap::Str and its data[1] are incompatible with ASAN guards
    # and the same happens with UBSAN and coverage somehow
    case $variant in
      (asan|ubsan|coverage)
        if test "$(basename $b)" = 'my_runtime_test'; then
          echo "SKIPPING $b because it's not compatible with $variant"
          continue
        fi
        ;;
   esac

    set +o errexit
    $b >$log 2>&1
    local status=$?
    set -o errexit

    if test "$status" -eq 0; then
      echo 'OK'
    else
      echo "FAIL with status $?"
      return $status
    fi
  done
}

soil-run() {
  unit '' testgc
  unit '' asan
  unit '' ubsan
}

unit-test-coverage() {
  ### Invoked by Soil

  unit clang coverage

  local out_dir=_test/clang-coverage/mycpp-unit 
  test/coverage.sh html-report $out_dir mycpp-unit
}

examples-coverage() {
  ### Invoked by Soil

  examples-variant clang coverage

  local out_dir=_test/clang-coverage/mycpp-examples
  test/coverage.sh html-report $out_dir mycpp-examples
}

"$@"
