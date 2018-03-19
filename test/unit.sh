#!/usr/bin/env bash
#
# Run unit tests.  Sets PYTHONPATH.
#
# Usage:
#   ./unit.sh <function name>
#
# Examples:
#
#   ./unit.sh one core/lexer_test.py
#   ./unit.sh all

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

export PYTHONPATH=.  # current dir

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
  echo ----
}

tests-to-run() {
  # TODO: Add opy.
  for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
    # For Travis after build/dev.sh minimal: if we didn't build fastlex.so,
    # then skip a unit test that will fail.
    if test $t = 'native/fastlex_test.py' && ! test -e 'fastlex.so'; then
      continue
    fi
    echo $t
  done
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
  time tests-to-run | xargs -n 1 -- $0 run-test-and-maybe-abort
  echo
  echo "All unit tests passed."
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
  local tasks_csv=$1
  local t=$2

  # NOTE: $t is assumed to be a relative path here!
  local log=_tmp/unit/$t.txt
  mkdir -p $(dirname $log)

  benchmarks/time.py --out $tasks_csv \
    --field $t --field "$t.txt" -- \
    $t >$log 2>&1
}

run-all-and-log() {
  local out_dir=_tmp/unit
  mkdir -p $out_dir
  rm -r -f $out_dir/*

  local tasks_csv=$out_dir/tasks.csv

  local status=0

  # TODO: I need to write a schema too?  Or change csv2html.py to support HREF
  # in NullSchema.

  echo 'status,elapsed_secs,test,test_HREF' > $tasks_csv
  time tests-to-run | xargs -n 1 -- $0 run-test-and-log $tasks_csv || status=1

  if test $status -ne 0; then
    cat $tasks_csv
    echo
    echo "*** Some tests failed.  See $tasks_csv ***"
    echo

    return $status
  fi

  #tree _tmp/unit
  echo
  echo "All unit tests passed."
}


source benchmarks/common.sh

# TODO: It would be nice to have timestamps of the underlying CSV files and
# timestamp of running the report.  This is useful for benchmarks too.

print-report() {
  local in_dir=${1:-_tmp/unit}
  local base_url='../../web'

  # NOTE: Using benchmarks for now.
  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>Unit Test Results</title>
    <script type="text/javascript" src="$base_url/table/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="$base_url/table/table-sort.css" />
    <link rel="stylesheet" type="text/css" href="$base_url/benchmarks.css" />

  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>Unit Test Results</h2>

EOF
  csv2html $in_dir/report.csv

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

# TODO: Also get rid of osh highlighting!

write-report() {
  local out=_tmp/unit/index.html
  test/report.R unit _tmp/unit _tmp/unit
  print-report > $out
  echo "Wrote $out"
}

# Called by scripts/release.sh.
run-for-release() {
  run-all-and-log
  write-report
}

"$@"
