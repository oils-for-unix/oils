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

banner() {
  echo -----
  echo "$@"
  echo -----
}

unit() {
  ### Run a single test, autocompletes with devtools/completion.bash
  local test_path=$1

  # Duplicates logic in test-niafest
  read -r first_line < $test_path
  if [[ $first_line == *python3* ]]; then
    py_path_more=:  # no-op
  else
    py_path_more=:vendor/  # for vendor/typing.py
  fi
  PYTHONPATH=${PYTHONPATH}${py_path_more} "$@"
}

test-files() {
  find . -name '_*' -a -prune -o -name '*_test.py' -a -printf '%P\n' | sort
}

test-manifest() {
  test-files | while read test_path; do
    local minimal=-
    case $test_path in
      # For build/py.sh minimal: if we didn't build fastlex.so,
      # then skip a unit test that will fail.
      pyext/fastlex_test.py|doctools/cmark_test.py)
        minimal=exclude
        ;;

      # Skip obsolete tests
      demo/old/*)
        continue
        ;;

      # Skip OPy and pgen2 tests - they have some PYTHONPATH issues?
      # May want to restore pgen2
      opy/*|pgen2/*)
        continue
        ;;

    esac

    read -r first_line < $test_path
    #echo $first_line
    if [[ $first_line == *python3* ]]; then
      kind=py3
      py_path_more=:  # no-op
    else
      kind=py2
      py_path_more=:vendor/  # for vendor/typing.py
    fi

    echo "$minimal $kind $py_path_more $test_path"
  done
}

files-to-count() {
  ### Invoked by metrics/source-code.sh
  test-manifest | while read _ _ _ test_path; do
    echo $test_path
  done
}

run-unit-test() {
  local py_path_more=$1
  local test_path=$2

  PYTHONPATH=${PYTHONPATH}${py_path_more} run-test-bin $test_path '' _test/py-unit
}

all() {
  ### Run unit tests after build/py.sh all

  test-manifest | while read minimal kind py_path_more test_path; do
    run-unit-test $py_path_more $test_path '' _test/py-unit
  done

  echo
  echo "All unit tests passed."
}

minimal() {
  ### Run unit tests after build/py.sh minimal

  test-manifest | while read minimal kind py_path_more test_path; do
    if test $minimal = exclude; then
      continue
    fi

    if test $kind = py3; then
      continue
    fi

    run-unit-test $py_path_more $test_path
  done

  echo
  echo "Minimal unit tests passed."
}

soil-run() {
  # TODO: Should run everything in CI, but it depends on R.  dev-minimal
  # doesn't have it
  #
  # Skips fastlex_test.py and cmark_test.py
  minimal
}

#
# Unlike soil-run, run-for-release makes an HTML page in _release/VERSION 
# Could unify them.

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

  # Not writing a schema
  tsv-row 'status' 'elapsed_secs' 'test' 'test_HREF' > $tasks_tsv

  # There are no functions here, so disabling errexit is safe.
  # Note: In YSH, this could use shopt { }.
  test-manifest | while read _ kind py_path_more test_path; do

    local status=0
    set +o errexit
    PYTHONPATH=${PYTHONPATH}${py_path_more} run-test-and-log $tasks_tsv $test_path
    status=$?
    set -o errexit

    if test $status -ne 0; then
      echo "FAIL $status - $test_path"
    fi

  done
}

# TODO: It would be nice to have timestamps of the underlying TSV files and
# timestamp of running the report.  This is useful for benchmarks too.

print-report() {
  local in_dir=${1:-_tmp/unit}
  local base_url='../../web'  # published at more_tests.wwz/unit/

  html-head --title 'Oils Unit Test Results' \
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

write-report() {
  # Presentation:
  #
  # - elapsed seconds -> milliseconds
  # - Link to test log
  # - Right justify numbers

  local out=_tmp/unit/index.html
  test/report.R unit _tmp/unit _tmp/unit
  print-report > $out
  echo "Wrote $out"
}

run-for-release() {
  # Invoked by devtools/release.sh.

  run-all-and-log
  write-report
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

run-task "$@"
