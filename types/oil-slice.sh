#!/usr/bin/env bash
#
# Test of the standalone parser.
#
# Usage:
#   types/oil-slice.sh <function name>
#
# Example:
#   types/oil-slice.sh soil-run

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source types/common.sh  # $MYPY_FLAGS

demo() {
  export PYTHONPATH='.:vendor/'

  echo 'echo hi' | bin/osh_parse.py
  bin/osh_parse.py -c 'ls -l'

  local osh_eval=${1:-bin/osh_eval.py}

  # Same functionality in bin/osh_eval
  echo 'echo hi' | $osh_eval
  $osh_eval -n -c 'ls -l'
  echo ---
  # ast format is none
  $osh_eval --ast-format none -n -c 'ls -l'

  echo '-----'

  # Now test some more exotic stuff
  $osh_eval -c '(( a = 1 + 2 * 3 ))'

  $osh_eval -c \
    'echo "hello"x $$ ${$} $((1 + 2 * 3)) {foo,bar}@example.com'

  $osh_eval -c 'for x in 1 2 3; do echo $x; done'
}

typecheck-all() {
  local manifest=$1
  local strict_none=${2:-}

  # 150 errors left without those flags.  But it doesn't impede translating to
  # C++ since you have nullptr.  Although List[Optional[int]] may be an issue.
  #local flags=''
  local flags
  if test -n "$strict_none"; then
    flags='--strict'
  else
    flags=$MYPY_FLAGS
  fi

  local log_path=_tmp/err.txt
  set +o errexit
  cat $manifest | xargs -- $0 typecheck --follow-imports=silent $flags >$log_path
  local status=$?
  set -o errexit
  if test $status -eq 0; then
    echo 'OK'
  else
    echo
    cat $log_path
    echo
    echo 'FAIL'
    return 1
  fi
}

soil-run() {
  if test -n "${TRAVIS_SKIP:-}"; then
    echo "TRAVIS_SKIP: Skipping $0"
    return
  fi

  # Figure out what to type check
  build/app-deps.sh osh-eval
  echo

  typecheck-all _build/app-deps/osh_eval/typecheck.txt
}

"$@"
