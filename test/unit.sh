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

one() {
  "$@"
}

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

# geez wtf!
repro() {
  rm -v *.pytrace || true
  delete-pyc

  #local t=osh/cmd_parse_test.py
  #local t='native/fastlex_test.py LexTest.testBug'
  local t='core/id_kind_test.py TokensTest.testEquality'

  # with shebang
  #py=''
  local py='_devbuild/cpython-instrumented/python'

  #local prefix='uftrace record -d one.uftrace'
  local prefix=''
  #local prefix='gdb --args'

  set +o errexit

  banner 'FIRST'

  $prefix $py $t
  local first=$?

  banner 'SECOND'

  # Fails the second time
  $prefix $py $t
  local second=$?

  echo "first $first  second $second"
  #$PY_273 -V
}

_log-one() {
  local name=$1
  $name > _tmp/unit/${name}.log.txt 2>&1
}

_all() {
  mkdir -p _tmp/unit

  # NOTE: build and test have small unit tests
  # TODO: Add opy.

  for t in {build,test,native,asdl,core,osh,tools}/*_test.py; do
    # NOTE: This test hasn't passed in awhile.  It uses strings as output.
    if [[ $t == *arith_parse_test.py ]]; then
      continue
    fi
    echo $t

    mkdir -p _tmp/unit/$(dirname $t)
    run-task-with-status _tmp/unit/${t}.task.txt $0 _log-one $t
  done
}

# spec-runner looks at .task.txt and .stats.txt.  We don't need that.  We just
# time, status, and a link to the .txt file.
_html-summary() {
  find _tmp/unit -name '*.task.txt' | awk '
  { path = $0
    getline < path
    status = $1
    wall_secs = $2

    if (status == 0) {
      num_passed += 1
    } else {
      num_failed = 1
      print path " failed"
    }
  }
  END {
    if (num_failed == 0) {
      print ""
      print "ALL " num_passed " TESTS PASSED"
    }
  }
  '
}

html-summary() {
  _html-summary
}

all() {
  time $0 _all
  html-summary
}

"$@"
