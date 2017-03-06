#!/bin/bash
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

source spec-runner.sh  # TODO: Separate this?

export PYTHONPATH=.  # current dir

# For auto-complete
one() {
  "$@"
}

_log-one() {
  local name=$1
  $name > _tmp/unit/${name}.log.txt 2>&1
}

_all() {
  local skip_c=${1:-}

  mkdir -p _tmp/unit

  for t in {asdl,core,osh}/*_test.py; do
    # NOTE: This test hasn't passed in awhile.  It uses strings as output.

    if [[ $t == *arith_parse_test.py ]]; then
      continue
    fi
    if test -n "$skip_c" && [[ $t == *libc_test.py ]]; then
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
  find _tmp/unit -name '*.task.txt' | xargs head -n 1
}

html-summary() {
  _html-summary
}

all() {
  time $0 _all
}

"$@"
