#!/usr/bin/env bash
#
# Collect and compare spec test results across different shells (and platforms
# eventually).
#
# Usage:
#   test/spec-compare.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source test/spec-common.sh

readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)

#
# For translation
#

osh-eval-py() {
  ### Run a suite with osh_eval.py (manual)
  local suite=${1:-arith}
  if test $# -gt 0; then
    shift
  fi
  test/spec.sh $suite $PWD/bin/osh_eval "$@"
}

osh-eval-cpp() {
  ### Run a suite with the translation of osh_eval.py (manual)
  local suite=${1:-arith}
  if test $# -gt 0; then
    shift
  fi
  test/spec.sh $suite $PWD/_bin/osh_eval.dbg "$@"
}

run-with-osh-eval() {
  ### Run a test with the given name.

  local test_name=$1
  shift

  # Run it with 3 versions of OSH.  And output TSV so we can compare the data.
  sh-spec spec/$test_name.test.sh \
    --tsv-output _tmp/spec/${test_name}.tsv \
    $REPO_ROOT/bin/osh \
    $REPO_ROOT/bin/osh_eval \
    $REPO_ROOT/_bin/osh_eval.dbg \
    "$@"
}

all-osh-eval() {
  ### Run all tests with osh_eval and its translatino
  export SPEC_RUNNER='test/spec-compare.sh run-with-osh-eval'

  # this is like test/spec.sh {oil,osh}-all
  test/spec-runner.sh all-parallel osh "$@"
}

summarize() {
  ### Print out a histogram of results

  awk '
FNR == 1 {
  #print FILENAME > "/dev/stderr" 
}
FNR != 1 {
  case_num = $1
  sh = $2
  result = $3

  if (sh == "osh") {
    osh[result] += 1
  } else if (sh == "oe.py") {
    oe_py[result] += 1
  } else if (sh == "oe.cpp") {
    oe_cpp[result] += 1
  }
}

function print_hist(sh, hist) {
  printf("%s\t", sh)

  k = "pass"
  printf("%s %4d\t", k, hist[k])
  k = "FAIL"
  printf("%s %4d\t", k, hist[k])

  print ""

  # This prints N-I, ok, bug, etc.
  #for (k in hist) {
  #  printf("%s %s\t", k, hist[k])
  #}

}

END { 
  print_hist("osh", osh)
  print_hist("oe.py", oe_py)
  print_hist("oe.cpp", oe_cpp)
}
  ' "$@"
}

osh-eval-report() {
  ### Report on our progress translating

  wc -l _tmp/spec/*.tsv

  for file in _tmp/spec/*.tsv; do
    echo
    echo "$file"
    summarize $file
  done

  echo
  echo "TOTAL"
  summarize _tmp/spec/*.tsv
}

tsv-demo() {
  sh-spec spec/arith.test.sh --tsv-output _tmp/arith.tsv dash bash "$@"
  cat _tmp/arith.tsv
}

# TODO:
# Instead of --stats-template 
# '%(num_cases)d %(osh_num_passed)d %(osh_num_failed)d %(osh_failures_allowed)d %(osh_ALT_delta)d' \
#
# Should you have a TSV file for each file?
# instead of if_.stats.txt, have if_.tsv
#
# And it will be:
# osh pass, osh fail, osh_ALT_delta = 0 or 1
# is --osh-failures-allowed something else?
#
# case osh eval.py eval.cpp
# Result.PASS, Result.FAIL
# Just sum the number of passes

"$@"
