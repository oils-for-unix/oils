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
#source build/dev-shell.sh
source build/ninja-rules-cpp.sh
source devtools/common.sh
source test/common.sh  # run-test-bin, can-compile-32-bit

# in case binaries weren't built
shopt -s failglob

# Will be needed to pass ASAN leak detector?  Or only do this for the main binary?
# export OILS_GC_ON_EXIT=1

examples-variant() {
  ### Run all examples using a variant -- STATS only

  local compiler=${1:-cxx}
  local variant=${2:-asan+gcalways}
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

  if test $num_failed -ne 0; then
    echo "FAIL: Expected no failures, got $num_failed"
    return 1
  fi

  return 0
}

#
# 3 Variants x {test, benchmark}
#

ex-gcalways() {
  local compiler=${1:-}
  examples-variant "$compiler" asan+gcalways
}

# TOO SLOW to run.  It's garbage collecting all the time.
ex-gcalways-bench() {
  local compiler=${1:-}
  examples-variant "$compiler" asan+gcalways '.BENCHMARK'
}

ex-asan() {
  local compiler=${1:-}
  examples-variant "$compiler" asan
}

# 2 of 18 tests failed: cartesian, parse
# So it does not catch the 10 segfaults that 'asan+gcalways' catches with a few
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

run-unit-tests() {

  local compiler=${1:-cxx}
  local variant=${2:-asan+gcalways}

  log ''
  log "$0 run-unit-tests $compiler $variant"
  log ''

  ninja mycpp-unit-$compiler-$variant

  local -a binaries=(_bin/$compiler-$variant/mycpp/*)

  # Add these files if they exist in the variant
  if test -d _bin/$compiler-$variant/mycpp/demo; then
    binaries+=(_bin/$compiler-$variant/mycpp/demo/*)
  fi

  for b in "${binaries[@]}"; do
    if ! test -f $b; then
      continue
    fi

    local prefix=${b//_bin/_test/}
    local log=$prefix.log
    mkdir -p $(dirname $log)

    local asan_options=''
    case $b in
      # leaks with malloc
      (*/demo/hash_table|*/demo/target_lang|*/demo/gc_header|*/small_str_test)
        asan_options='detect_leaks=0'
        ;;
    esac

    ASAN_OPTIONS="$asan_options" run-test-bin $b

  done
}

#
# Test failures
#

translate-example() {
  local ex=$1

  local mycpp=_bin/shwrap/mycpp_main
  $mycpp '.:pyext' _tmp/mycpp-invalid $ex
}

test-invalid-examples() {
  local mycpp=_bin/shwrap/mycpp_main
  ninja $mycpp
  for ex in mycpp/examples/invalid_*; do

    banner "$ex"

    set +o errexit
    translate-example $ex
    local status=$?
    set -o errexit

    local expected_status=1

    case $ex in 
      */invalid_condition.py)
        # forward decl pass catches some, but not all
        expected_status=5
        ;;
      */invalid_other.py)
        expected_status=4
        ;;
      */invalid_default_args.py)
        expected_status=4
        ;;
      */invalid_try_else.py)
        expected_status=3
        ;;
      */invalid_except.py)
        expected_status=3
        ;;
      */invalid_global.py)
        expected_status=2
        ;;
      */invalid_python.py)
        expected_status=5
        ;;
      */invalid_switch.py)
        expected_status=5
        ;;
    esac

    if test $status -ne $expected_status; then
      die "mycpp $ex: expected status $expected_status, got $status"
    fi

  done
}

test-control-flow-graph() {
  local mycpp=_bin/shwrap/mycpp_main
  ninja $mycpp
  for ex in mycpp/examples/*.py; do
    local data_dir=testdata/control-flow-graph/$(basename -s .py $ex)
    if ! test -d $data_dir; then
      continue
    fi
    banner "$ex"

    translate-example $ex
    for fact_path in $data_dir/*.facts; do
      local fact_file=$(basename $fact_path)
      diff -u $data_dir/$fact_file _tmp/mycpp-facts/$fact_file
    done
  done
}

# TODO: Run with Clang UBSAN in CI as well
readonly UBSAN_COMPILER=cxx

unit() {
  ### Run by test/cpp-unit.sh

  # Run other unit tests, e.g. the GC tests

  if can-compile-32-bit; then
    run-unit-tests '' asan32+gcalways  # ASAN on 32-bit
  else
    log ''
    log "*** Can't compile 32-bit binaries (gcc-multilib g++-multilib needed on Debian)"
    log ''
  fi

  # Run other tests with all variants

  run-unit-tests $UBSAN_COMPILER ubsan

  run-unit-tests '' asan
  run-unit-tests '' asan+gcalways
  run-unit-tests '' opt
  run-unit-tests '' asan+bigint

  bump-leak-heap-test
}

bump-leak-heap-test() {
  for config in cxx-asan+bumpleak $UBSAN_COMPILER-ubsan+bumpleak; do
    local bin=_bin/$config/mycpp/bump_leak_heap_test
    ninja $bin
    run-test-bin $bin
  done
}

#
# Translator
#

test-translator() {
  ### Invoked by soil/worker.sh

  examples-variant '' asan

  # Test with more collections
  examples-variant '' asan+gcalways

  run-test-func test-invalid-examples _test/mycpp/test-invalid-examples.log

  run-test-func test-control-flow-graph _test/mycpp/test-cfg-examples.log

  # Runs tests in cxx-asan variant, and benchmarks in cxx-opt variant
  if ! ninja mycpp-logs-equal; then
    log 'FAIL mycpp-logs-equal'
    return 1
  fi
}

soil-run() {
  set +o errexit
  $0 test-translator
  local status=$?
  set -o errexit

  return $status
}

unit-test-coverage() {
  ### Invoked by Soil

  local bin=_bin/clang-coverage+bumpleak/mycpp/bump_leak_heap_test
  ninja $bin
  run-test-bin $bin

  run-unit-tests clang coverage

  local out_dir=_test/clang-coverage/mycpp
  test/coverage.sh html-report $out_dir \
    clang-coverage/mycpp clang-coverage+bumpleak/mycpp
}

examples-coverage() {
  ### Invoked by Soil

  examples-variant clang coverage

  local out_dir=_test/clang-coverage/mycpp/examples
  test/coverage.sh html-report $out_dir clang-coverage/mycpp/examples
}

mycpp-check() {
  if true; then
    #python3 -m mypy --strict --follow-imports=silent "$@"
    python3 -m mypy --strict --no-strict-optional --follow-imports=silent "$@"
  else
    # Disable --strict until more passes - 308 -> 181 errors
    # That means that types are optional
    # Also add --no-strict-optional
    python3 -m mypy --no-strict-optional --follow-imports=silent "$@"
  fi
}

check-types() {
  local p=".:$MYPY_WEDGE:$PY3_LIBS_WEDGE"

  #local -a files=( mycpp/*.py )
  local -a files=(
    mycpp/{pass_state,util,crash,format_strings,visitor,ir_pass,const_pass,control_flow_pass,mycpp_main,cppgen_pass}.py
  )

  # the path is fiddly
  PYTHONPATH=$p MYPYPATH=$MYPY_WEDGE \
    mycpp-check "${files[@]}"
}

files() {
  wc -l mycpp/*.py | sort -n
}

# Call function $1 with arguments $2 $3 $4
#
# mycpp/TEST.sh examples-variant '' asan

"$@"
