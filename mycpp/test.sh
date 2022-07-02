#!/usr/bin/env bash
#
# Usage:
#   mycpp/test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

export ASAN_OPTIONS='detect_leaks=0'

examples-variant() {
  ### Run all examples using a variant

  local variant=$1
  local do_benchmark=${2:-}

  # This also builds unit tests, which we don't want
  # mycpp-ex-asan?
  ninja mycpp-$variant

  set +o errexit

  local num_tests=0
  local num_failed=0
  local status=0

  local log_dir=_test/cxx-$variant/mycpp-examples
  mkdir -p $log_dir

  for b in _bin/cxx-$variant/mycpp-examples/*; do
    case $b in
      (*.stripped)  # just run the unstripped binary
        continue
        ;;
    esac

    local log=$log_dir/$(basename $b)${do_benchmark}.log
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
  examples-variant testgc
}

# TOO SLOW to run.  It's garbage collecting all the time.
ex-testgc-bench() {
  examples-variant testgc '.BENCHMARK'
}

# PASS!
ex-asan() {
  examples-variant asan
}

# 2 of 18 tests failed: cartesian, parse
# So it does not catch the 10 segfaults that 'testgc' catches with a few
# iterations!
ex-asan-bench() {
  examples-variant asan '.BENCHMARK'
}

# PASS!
ex-ubsan() {
  examples-variant ubsan
}

# same as ASAN: 2 of 18
ex-ubsan-bench() {
  examples-variant ubsan '.BENCHMARK'
}

# PASS!
ex-opt() {
  examples-variant opt
}

# 2 of 18 tests failed
ex-opt-bench() {
  examples-variant opt '.BENCHMARK'
}

unit() {
  ### Run by test/cpp-unit.sh

  local variant=${1:-testgc}

  ninja mycpp-unit

  local log_dir=_test/cxx-$variant/unit
  mkdir -p $log_dir

  for b in _bin/cxx-$variant/mycpp-unit/*; do
    local log=$log_dir/$(basename $b).log
    echo "RUN $b > $log"

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

"$@"
