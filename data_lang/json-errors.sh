#!/usr/bin/env bash
#
# Usage:
#   data_lang/json-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh  # $OSH
source test/sh-assert.sh  # banner, _assert-sh-status

# Test JSON in OSH.  Should be the same in YSH.
#OSH=${OSH:-bin/osh}

_error-case-X() {
  local expected_status=$1
  shift

  local message=$0
  _assert-sh-status $expected_status $OSH "$message" \
    -c "$@"
}

_expr-error-case() {
  ### Expect status 3
  _error-case-X 3 "$@"
}

#
# Cases
#

test-parse-errors() {
  #echo OSH=$OSH
  #set +o errexit

  # Unexpected EOF
  _error-case-X 1 'echo "" | json read'

  # Unexpected token
  _error-case-X 1 'echo { | json read'

  # Invalid token
  _error-case-X 1 'echo + | json read'
}

test-lex-errors() {
  # Unclosed quote
  _error-case-X 1 'echo [\" | json read'

  # EOL in middle of string
  _error-case-X 1 'echo -n [\" | json read'

  # Invalid unicode

  json=$'"\xce"'  # part of mu = \u03bc
  echo "json=$json"
  json=${json//'"'/'\"'}  # shell escape
  _error-case-X 1 $'echo -n '$json' | json read'
}

test-encode() {
  _error-case-X 1 'var d = {}; setvar d.k = d; json write (d)'

  _error-case-X 1 'var L = []; call L->append(L); json write (L)'

  # This should fail!
  # But not pp line (L)
  _error-case-X 1 'var L = []; call L->append(/d+/); j8 write (L)'
}

#
# Entry points
#

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  # This is like run-test-funcs, except errexit is off here
  ninja _bin/cxx-asan/osh
  #OSH=_bin/cxx-asan/osh run-test-funcs

  echo TODO: enable
}

run-for-release() {
  run-other-suite-for-release json-errors run-test-funcs
}

"$@"
