#!/usr/bin/env bash
#
# Usage:
#   mycpp/test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

export ASAN_OPTIONS='detect_leaks=0'

run-variant() {
  ### Run all examples using a variant

  local variant=$1
  local do_benchmark=${2:-}

  ninja mycpp-$variant

  set +o errexit

  local num_tests=0
  local num_failed=0
  local status=0

  for b in _test/bin/examples-mycpp/*.$variant; do
    echo $b

    # TODO: write to a log

    local test_name=$(basename $b)
    if test -n "$do_benchmark" && [[ $test_name == test_* ]]; then
      echo "Skipping $test_name in benchmark mode"
      continue
    fi

    BENCHMARK="$do_benchmark" $b >/dev/null 2>&1

    status=$?
    echo "status $status"

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
testgc() {
  run-variant testgc
}

# TOO SLOW to run.  It's garbage collecting all the time.
testgc-bench() {
  run-variant testgc 1
}

# PASS!
asan() {
  run-variant asan
}

# 2 of 18 tests failed: cartesian, parse
# So it does not catch the 10 segfaults that 'testgc' catches with a few
# iterations!
asan-bench() {
  run-variant asan 1
}

# PASS!
ubsan() {
  run-variant ubsan
}

# same as ASAN: 2 of 18
ubsan-bench() {
  run-variant ubsan 1
}

# PASS!
opt() {
  run-variant opt
}

# 2 of 18 tests failed
opt-bench() {
  run-variant opt 1
}

unit() {
  ### Run by test/cpp-unit.sh

  local variant=${1:-testgc}

  ninja mycpp-unit

  local log_dir=_test/unit
  mkdir -p $log_dir

  for b in _test/bin/unit/*.$variant; do
    local log=$log_dir/$(basename $b) 
    echo "log $log"

    $b >$log 2>&1
    local status=$?

    echo "status $status"
  done
}

"$@"
