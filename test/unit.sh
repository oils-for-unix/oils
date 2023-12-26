#!/usr/bin/env bash
#
# Run unit tests.  Sets PYTHONPATH.
#
# Usage:
#   test/unit.sh <function name>
#
# Examples:
#
#   test/unit.sh unit frontend/lexer_test.py
#   test/unit.sh all
#   test/unit.sh minimal

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source build/dev-shell.sh    # R_LIBS_USER, but also changes python3
source test/common.sh        # html-head
source devtools/run-task.sh  # run-task
source test/tsv-lib.sh

# for 'import typing' in Python 2. Can't go in build/dev-shell.sh because it
# would affect Python 3.
export PYTHONPATH="vendor:$PYTHONPATH"

# For auto-complete
unit() {
  "$@"
}

delete-pyc() {
  find . -name '*.pyc' | xargs --no-run-if-empty -- rm || true
}

# WTF, fixes native_test issue
#export PYTHONDONTWRITEBYTECODE=1

banner() {
  echo -----
  echo "$@"
  echo -----
}

readonly -a PY2_UNIT_TESTS=( {asdl,asdl/examples,build,builtin,core,data_lang,doctools,frontend,lazylex,ysh,osh,pyext,pylib,soil,test,tools}/*_test.py )

readonly -a PY3_UNIT_TESTS=( mycpp/*_test.py spec/stateful/*_test.py )

py2-tests() {
  local minimal=${1:-}

  for t in "${PY2_UNIT_TESTS[@]}"; do
    # For Travis after build/py.sh minimal: if we didn't build fastlex.so,
    # then skip a unit test that will fail.

    if test -n "$minimal"; then
      if test $t = 'pyext/fastlex_test.py'; then
        continue
      fi
      # doctools/cmark.sh makes that shared library
      if test $t = 'doctools/cmark_test.py'; then
        continue
      fi
    fi

    echo $t
  done
}

py3-tests() {
  for t in "${PY3_UNIT_TESTS[@]}"; do
    echo $t
  done
}

all-tests() {
  py2-tests "$@"

  # TODO: This only PRINTS the tests.  It doesn't actually run them, but we
  # need a different PYTHONPATH here.
  py3-tests
}

run-unit-tests() {
  while read test_path; do
    # no separate working dir
    run-test-bin $test_path '' _test/py-unit
  done
}

all() {
  ### Run unit tests after build/py.sh all

  time all-tests "$@" | run-unit-tests
  echo
  echo "All unit tests passed."
}

minimal() {
  ### Run unit tests after build/py.sh minimal

  time py2-tests T | run-unit-tests
  echo
  echo "Minimal unit tests passed."
}

#
# Experimental tsv-stream
#

tsv-stream-one() {
  local rel_path=$1

  local log_file=_tmp/unit/$rel_path.txt
  mkdir -p "$(dirname $log_file)"

  echo
  echo "| ROW test=$rel_path test_HREF=$log_file"

  # TODO: Emit | ADD status=0 elapsed_secs=0.11

  time-tsv -o /dev/stdout -- $rel_path
  local status=$?

  if test $status -ne 0; then
    echo
    echo "*** $t FAILED ***"
    echo
    return 255  # xargs aborts
  fi

}

tsv-stream-all() {
  echo '| HEADER status elapsed_secs test test_HREF'

  time py2-tests T | head -n 20 | xargs -n 1 -- $0 tsv-stream-one
}

# Experimental idea: Capture tsv-stream-all, and turn it into two things:
#
# - A TSV file, which can be turned into HTML, and summarized with counts
# - An HTML text string with <a name=""> anchors, which the table can link to
#
# At the terminal, the raw output is still readable, without a filter.
# Although we might want:
#
# | OK
# | FAIL
#
# Instead of:
#
# | ADD status=0
# | ADD status=1
#
# Also, we currently send output to /dev/null at the terminal, and we save it
# when doing a release.
#
# We might also do something like C++ unit tests:
# 
# RUN osh/split_test.py &> _test/osh/split_test


all-2() {
  ### New harness that uses tsv-stream

  # Use this at the command line, in the CI, and in the release.

  tsv-stream-all | devtools/tsv_stream.py
}

# NOTE: Show options like this:
# python -m unittest discover -h

#
# For _release/VERSION
#

run-test-and-log() {
  local tasks_tsv=$1
  local rel_path=$2

  local log=_tmp/unit/$rel_path.txt
  mkdir -p "$(dirname $log)"

  time-tsv --append --out $tasks_tsv \
    --field $rel_path --field "$rel_path.txt" -- \
    $rel_path >$log 2>&1
}

run-all-and-log() {
  local out_dir=_tmp/unit
  mkdir -p $out_dir
  rm -r -f $out_dir/*

  local tasks_tsv=$out_dir/tasks.tsv

  local status=0

  # TODO: I need to write a schema too?  Or change csv2html.py to support HREF
  # in NullSchema.

  tsv-row 'status' 'elapsed_secs' 'test' 'test_HREF' > $tasks_tsv

  # There are no functions here, so disabline errexit is safe.
  # Note: In Oil, this could use shopt { }.
  set +o errexit
  time all-tests | xargs -n 1 -- $0 run-test-and-log $tasks_tsv
  status=$?
  set -o errexit

  if test $status -ne 0; then
    cat $tasks_tsv
    echo
    echo "*** Some tests failed.  See $tasks_tsv ***"
    echo

    return $status
  fi

  #tree _tmp/unit
  echo
  echo "All unit tests passed."
}


# TODO: It would be nice to have timestamps of the underlying CSV files and
# timestamp of running the report.  This is useful for benchmarks too.

print-report() {
  local in_dir=${1:-_tmp/unit}
  local base_url='../../web'  # published at more_tests.wwz/unit/

  html-head --title 'Oil Unit Test Results' \
    "$base_url/table/table-sort.js" \
    "$base_url/table/table-sort.css" \
    "$base_url/base.css" \
    "$base_url/benchmarks.css" 

  # NOTE: Using benchmarks for now.
  cat <<EOF
  <body class="width40">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>Unit Test Results</h2>

EOF

  tsv2html $in_dir/report.tsv

  cat <<EOF
  </body>
</html>
EOF
}

# Presentation changes:
#
# - elapsed seconds -> milliseconds
# - Need a link to the log for the test name (done, but no schema)
# - schema for right-justifying numbers

write-report() {
  local out=_tmp/unit/index.html
  test/report.R unit _tmp/unit _tmp/unit
  print-report > $out
  echo "Wrote $out"
}

soil-run() {
  # TODO: Should run everything in CI, but it depends on R.  dev-minimal
  # doesn't have it
  #
  # Skips fastlex_test.py and cmark_test.py
  minimal
}

# Called by scripts/release.sh.
run-for-release() {
  run-all-and-log
  write-report
}

run-task "$@"
