#!/usr/bin/env bash
#
# Test the C++ translation of Oil.
#
# Usage:
#   test/spec-cpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # html-head
source test/spec-common.sh
source web/table/html.sh

shopt -s failglob  # to debug TSV expansion failure below

readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)

# For now use opt since it's faster, see issue #970
readonly OSH_CC=$REPO_ROOT/_bin/osh_eval.opt

# Applies everywhere
export SPEC_JOB='cpp'
export ASAN_OPTIONS=detect_leaks=0

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
  #test/spec.sh $suite $PWD/_bin/osh_eval.dbg "$@"

  test/spec.sh $suite $OSH_CC "$@"
}

osh-eval-asan() {
  _bin/osh_eval.asan "$@"
}

asan-smoke() {
  _bin/osh_eval.asan -c 'echo hi'
  echo 'echo hi' | _bin/osh_eval.asan
}

run-with-osh-eval() {
  ### Run a test with the given name.

  local test_name=$1
  shift

  local base_dir=_tmp/spec/$SPEC_JOB

  # Run it with 3 versions of OSH.  And output TSV so we can compare the data.
  sh-spec spec/$test_name.test.sh \
    --tsv-output $base_dir/${test_name}.tsv \
    $REPO_ROOT/bin/osh \
    $REPO_ROOT/bin/osh_eval \
    $OSH_CC \
    "$@"
}

all() {
  ### Run all tests with osh_eval and its translatino
  export SPEC_RUNNER='test/spec-cpp.sh run-with-osh-eval'
  #export NUM_SPEC_TASKS=4
  # For debugging hangs
  #export MAX_PROCS=1

  # this is like test/spec.sh {oil,osh}-all

  # Hack: got rid of hanging 'redirect' suite in spec-runner.sh manifest
  # TODO: fix that and switch back to 'osh' suite
  local suite=osh-cpp
  test/spec-runner.sh all-parallel $suite "$@" || true  # OK if it fails

  html-summary
}

travis() {
  # Run serially on Travis?  It hung once
  # export MAX_PROCS=1

  # Hack, build with GCC because of startup time issue #970
  CXX=gcc build/mycpp.sh compile-slice-opt

  # Do less work to start
  # export NUM_SPEC_TASKS=8
  all
}

console-row() {
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
  } else if (sh == "osh_.py") {
    oe_py[result] += 1
  } else if (sh == "osh_.cc") {
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
  print_hist("osh_.py", oe_py)
  print_hist("osh_.cc", oe_cpp)
}
  ' "$@"
}

console-summary() {
  ### Report on our progress translating

  # Can't go at the top level because files won't exist!
  readonly TSV=(_tmp/spec/cpp/*.tsv)

  wc -l "${TSV[@]}"

  for file in "${TSV[@]}"; do
    echo
    echo "$file"
    console-row $file
  done

  echo
  echo "TOTAL"
  console-row "${TSV[@]}"
}

#
# HTML
#

summary-csv-row() {
  ### Print one row or the last total row

  if test $# -eq 1; then
    local tsv_path=$1
    local spec_name=$(basename "$tsv_path" .tsv)
  else
    local spec_name='TOTAL'
  fi

  awk -v spec_name=$spec_name '
# skip the first row
FNR != 1 {
  case_num = $1
  sh = $2
  result = $3

  if (sh == "osh") {
    osh[result] += 1
  } else if (sh == "osh_.py") {
    osh_eval_py[result] += 1
  } else if (sh == "osh_.cc") {
    osh_eval_cpp[result] += 1
  }
}

END { 
  num_osh = osh["pass"]
  num_py = osh_eval_py["pass"] 
  num_cpp = osh_eval_cpp["pass"]
  if (spec_name == "TOTAL") {
    href = ""
  } else {
    href = sprintf("%s.html", spec_name)
  }

  if (num_osh == num_py) {
    row_css_class = "py-good"  # yellow

    if (num_py == num_cpp) {
      row_css_class = "cpp-good"  # upgrade to green
    }
  }

  printf("%s,%s,%s,%d,%d,%d,%d,%d\n",
         row_css_class,
         spec_name, href,
         num_osh,
         num_py,
         num_osh - num_py,
         num_cpp,
         num_py - num_cpp)
}
  ' "$@"
}

summary-csv() {
  # Can't go at the top level because files might not exist!
  readonly TSV=(_tmp/spec/cpp/*.tsv)

  cat <<EOF
ROW_CSS_CLASS,name,name_HREF,osh,osh_eval.py,delta_py,osh_eval.cpp,delta_cpp
EOF

  # total row rows goes at the TOP, so it's in <thead> and not sorted.
  summary-csv-row "${TSV[@]}"

  for file in "${TSV[@]}"; do
    summary-csv-row $file
  done
}

html-summary-header() {
  local prefix=../../..
  html-head --title 'Passing Spec Tests in C++' \
    $prefix/web/ajax.js \
    $prefix/web/table/table-sort.js $prefix/web/table/table-sort.css \
    $prefix/web/base.css \
    $prefix/web/spec-cpp.css

  table-sort-begin "width50"

  cat <<EOF
<p id="home-link">
  <!-- The release index is two dirs up -->
  <a href="../..">Up</a> |
  <a href="/">oilshell.org</a>
</p>

<h1>Passing Spec Tests</h1>

<p>These numbers measure the progress of Oil's C++ translation.</p>

EOF
}

html-summary-footer() {
  cat <<EOF
<p><a href="osh.html">osh.html</a></p>
EOF
  table-sort-end "$@"
}

readonly BASE_DIR=_tmp/spec/cpp

here-schema() {
  ### Read a legible text format on stdin, and write CSV on stdout

  # This is a little like: https://wiki.xxiivv.com/site/tablatal.html
  # TODO: generalize this in stdlib/here.sh
  while read one two; do
    echo "$one,$two"
  done
}

html-summary() {
  local name=summary

  local out=$BASE_DIR/osh-summary.html

  summary-csv >$BASE_DIR/summary.csv 

  # The underscores are stripped when we don't want them to be!
  # Note: we could also put "pretty_heading" in the schema

  here-schema >$BASE_DIR/summary.schema.csv <<EOF
column_name   type
ROW_CSS_CLASS string
name          string
name_HREF     string
osh           integer
osh_eval.py   integer
delta_py      integer
osh_eval.cpp  integer
delta_cpp     integer
EOF

  { html-summary-header
    # total row isn't sorted
    web/table/csv2html.py --thead-offset 1 $BASE_DIR/summary.csv
    html-summary-footer $name
  } > $out
  echo "Wrote $out"
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

one-off() {
  set +o errexit

  # pure problem, backslashes

  # this might be an IFS problem, because backslashes are missing from the
  # unquoted one
  run-with-osh-eval quote -r 11 -v

  # not sure
  run-with-osh-eval prompt -r 3 -v

  return

  # redirects is nullptr problem
  run-with-osh-eval for-expr -r 2 -v

  run-with-osh-eval builtin-io -r 9 -v  # \0
  run-with-osh-eval assign-extended -r 9 -v  # declare -p, crash

  # xtrace: unicode
  return

  # printf: putenv() and strftime, and %5d

  # unicode.  I think this is a libc glob setting
  run-with-osh-eval var-op-strip -r 10 -v
  run-with-osh-eval var-op-strip -r 24 -v

  #run-with-osh-eval builtin-io -r 26 -v  # posix::read
  #run-with-osh-eval builtin-io -r 54 -v  # to_float()
}

"$@"
