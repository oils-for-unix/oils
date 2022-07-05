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

  # TODO: Exclude examples here
  # ninja mycpp-$variant
  ninja mycpp-unit-$compiler-$variant

  local log_dir=_test/$compiler-$variant/mycpp-unit
  mkdir -p $log_dir

  for b in _bin/$compiler-$variant/mycpp-unit/*; do
    local prefix=$log_dir/$(basename $b)
    local log=$prefix.log

    echo "RUN $b > $log"

    if test "$variant" = 'coverage'; then
      export LLVM_PROFILE_FILE=$prefix.profraw
      if test "$(basename $b)" = 'my_runtime_test'; then
        echo "SKIPPING $b"
        continue
      fi
    fi

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

unit-test-coverage() {
  # Hm same crash here
  unit clang coverage
  ls -l _test/clang-coverage/mycpp-unit/*.profraw
}

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/common.sh  # $CLANG_DIR

coverage-report() {
  local dir=_test/clang-coverage/mycpp-unit

  $CLANG_DIR/bin/llvm-profdata merge -sparse $dir/*.profraw \
    -o $dir/ALL.profdata \

  ls -l $dir

  # https://llvm.org/docs/CommandGuide/llvm-cov.html
  # Weird syntax
  local bin_dir=_bin/clang-coverage/mycpp-unit

  local -a args=()
  for b in $bin_dir/*; do
    args+=(--object $b)
  done

  echo 'ALL'

  $CLANG_DIR/bin/llvm-cov show --instr-profile $dir/ALL.profdata "${args[@]}"

  local html=$dir/REPORT.html
  local html_dir=$dir/html
  mkdir -p $html_dir

  $CLANG_DIR/bin/llvm-cov show \
    --format html --output-dir $html_dir \
    --instr-profile $dir/ALL.profdata \
    "${args[@]}"

  #echo "Wrote $html"
  #ls -l --si -h $html  # 2.2 MB of HTML

  # 2.4 MB of HTML
  du --si -s $html_dir

  echo
  echo

  $CLANG_DIR/bin/llvm-cov report --instr-profile=$dir/ALL.profdata "${args[@]}"

  # Also TODO: leaky_bindings_test, etc.
}

"$@"
