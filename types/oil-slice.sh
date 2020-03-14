#!/bin/bash
#
# Test of the standalone parser.
#
# Usage:
#   ./osh_parse.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source types/common.sh

demo() {
  export PYTHONPATH=.

  echo 'echo hi' | bin/osh_parse.py
  bin/osh_parse.py -c 'ls -l'

  local osh_eval=${1:-bin/osh_eval.py}

  # Same functionality in bin/osh_eval
  echo 'echo hi' | $osh_eval
  $osh_eval -n -c 'ls -l'
  echo ---
  # ast format is none
  $osh_eval -a none -n -c 'ls -l'

  echo '-----'

  # Now test some more exotic stuff
  $osh_eval -c '(( a = 1 + 2 * 3 ))'

  $osh_eval -c \
    'echo "hello"x $$ ${$} $((1 + 2 * 3)) {foo,bar}@example.com'

  $osh_eval -c 'for x in 1 2 3; do echo $x; done'
}

readonly OSH_PARSE_DEPS='_tmp/osh_parse-deps.txt'
readonly OSH_EVAL_DEPS='_tmp/osh_eval-deps.txt'

deps() {
  local prog=$1

  local pythonpath='.:vendor'
  local out=_build/$prog
  mkdir -p $out
  build/actions.sh app-deps $prog "$pythonpath" bin.$prog

  ls -l $out

  #head -n 30 $out/*

  echo ---

  # Around 16K lines, after stripping down the 'typing' module.

  awk '
  $1 ~ /^.*\.py$/ { print $1 }
  ' $out/app-deps-cpython.txt \
    | grep -v __init__ | sort | tee _tmp/${prog}-deps.txt | xargs wc -l | sort -n
}

osh-parse-deps() { deps osh_parse; }
osh-eval-deps() { deps osh_eval; }

egrep-deps() {
  cat $OSH_EVAL_DEPS | xargs -- egrep "$@"
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

  set +o errexit
  cat $manifest | xargs -- $0 typecheck --follow-imports=silent $flags >_tmp/err.txt
  #echo "status: $?"

  assert-one-error _tmp/err.txt
}

# The manifest needs to be checked in because we don't have
# _devbuild/cpython-full on Travis to crawl dependencies.
travis-setup() {
  # TODO: add stat.py back.  Why does it cause errors?
  local exclude='vendor|__future__|mylib.py|/stat.py'

  osh-parse-deps
  egrep -v "$exclude" $OSH_PARSE_DEPS | tee $OSH_PARSE_MANIFEST
  osh-eval-deps
  egrep -v "$exclude" $OSH_EVAL_DEPS | tee $OSH_EVAL_MANIFEST
}

compare-parse-eval() {
  diff -u types/osh-{parse,eval}-manifest.txt
}

travis() {
  if test -n "${TRAVIS_SKIP:-}"; then
    echo "TRAVIS_SKIP: Skipping $0"
    return
  fi

  #typecheck-all $OSH_PARSE_MANIFEST
  typecheck-all $OSH_EVAL_MANIFEST
}

"$@"
