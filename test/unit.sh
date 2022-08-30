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

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source test/common.sh
source test/tsv-lib.sh

export PYTHONPATH='.:vendor'  # repo root and vendor subdir

# For auto-complete
unit() {
  #$py "$@"

  "$@"
}

delete-pyc() {
  find . -name '*.pyc' | xargs --no-run-if-empty -- rm || true
}

readonly PY_273=~/src/languages/Python-2.7.3/python
readonly PY_272=~/src/languages/Python-2.7.2/python
readonly PY_27=~/src/languages/Python-2.7/python

# WTF, fixes native_test issue
#export PYTHONDONTWRITEBYTECODE=1

banner() {
  echo -----
  echo "$@"
  echo -----
}

readonly -a PY2_UNIT_TESTS=( {asdl,asdl/examples,build,core,doctools,frontend,lazylex,oil_lang,osh,pyext,pylib,qsn_,test,tools}/*_test.py )

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

# Exits 255 if a test fails.
run-test-and-maybe-abort() {
  local t=$1
  echo
  echo "[$t]"
  if ! $t >/dev/null; then
    echo
    echo "*** $t FAILED ***"
    echo
    return 255  # xargs aborts
  fi
  #echo "OK    $t"
}

all() {
  ### Run unit tests after build/py.sh all

  time all-tests "$@" | xargs -n 1 -- $0 run-test-and-maybe-abort
  echo
  echo "All unit tests passed."
}

minimal() {
  ### Run unit tests after build/py.sh minimal

  time py2-tests T | xargs -n 1 -- $0 run-test-and-maybe-abort
  echo
  echo "Minimal unit tests passed."
}

soil-run() {
  if test -n "${TRAVIS_SKIP:-}"; then
    echo "TRAVIS_SKIP: Skipping $0"
    return
  fi

  minimal
}

# Run all unit tests in one process.
all-in-one() {
  # -s: start dir -t: top level are defaults
  # NOTE: without the pattern, it finds byterun unit tests called 'test*'.
  _OVM_RESOURCE_ROOT=$PWD python -m unittest discover \
    --failfast --verbose --pattern '*_test.py'

  # This style fails due to the arguments being filenames and not Python module
  # names.
  #tests-to-run | xargs python -m unittest

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
  local base_url='../../web'

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
  R_LIBS_USER=$R_PATH test/report.R unit _tmp/unit _tmp/unit
  print-report > $out
  echo "Wrote $out"
}

# Called by scripts/release.sh.
run-for-release() {
  run-all-and-log
  write-report
}

"$@"
