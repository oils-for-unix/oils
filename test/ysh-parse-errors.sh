#!/usr/bin/env bash
#
# Usage:
#   test/ysh-parse-errors.sh <function name>

source test/common.sh
source test/sh-assert.sh  # banner, _assert-sh-status

YSH=${YSH:-bin/ysh}

_should-parse() {
  local message='Should parse under YSH'
  _assert-sh-status 0 $YSH "$message" \
    -n -c "$@"
}

_error-case() {
  local message='Should NOT parse under YSH'
  _assert-sh-status 2 $YSH "$message" \
    -n -c "$@"
}

test-return-args() {
  set +o errexit

  _should-parse '
  func foo(x) {
    return (x)
  }
  '

  _error-case '
  func foo(x) {
    return ()
  }
  '

  _error-case '
  func foo(x) {
    return (named=x)
  }
  '

  _error-case '
  func foo(x) {
    return (x, named=x)
  }
  '

  _error-case '
  func foo(x) {
    return (x, x)
  }
  '
}

test-func-var-checker() {
  set +o errexit

  _should-parse '
  func f(x) {
    setvar x = True
  }
  '

  _error-case '
  func f() {
    setvar x = True
  }
  '
}

# Extra constraints on param groups:
# - word arg types can only be Str or Ref
# - no constraints on positional or keyword args?
#   - they have optional types, and optional default vals
# - block param:
#   - there can only be one
#   - no rest param either
#   - default value is null only?

test-proc-sig() {
  _should-parse 'proc p () { echo hi }'
  _should-parse 'proc p (a) { echo hi }'
  _should-parse 'proc p (out Ref) { echo hi }'

  # doesn't make sense I think -- they're all strings.  Types don't do any
  # dynamic validation, except 'out Ref' does change semantics
  _error-case 'proc p (a Int) { echo hi }'

  _error-case 'proc p (w, ...) { echo hi }'

  _should-parse 'proc p (w, ...rest) { echo hi }'

  # Hm I guess this is fine
  _should-parse 'proc p (; n Int=3) { echo hi }'

  _should-parse 'proc p (out Ref; n Int=3) { echo hi }'

  _should-parse 'proc p (; ; n Int=3) { echo hi }'

  _should-parse 'proc p ( ; ; ; block) { echo hi }'

  _should-parse 'proc p (w, ...rest) { echo hi }'
  _should-parse 'proc p (w, ...rest; t) { echo hi }'

  _should-parse 'func p (p, ...rest) { echo hi }'

  _should-parse 'func p (p, ...rest; n, ...rest) { echo hi }'
  _should-parse 'func p (p, ...rest; n, ...rest,) { echo hi }'

  _error-case 'func p (p, ...rest; n, ...rest, z) { echo hi }'
  _error-case 'func p (p, ...rest; n, ...rest; ) { echo hi }'

  _should-parse 'proc p (w, ...rest; pos, ...rest) { echo hi }'

  _should-parse 'proc p (w, ...rest; pos, ...rest; named=3, ...rest) { echo hi }'

  _should-parse 'proc p (w=1, v=2; p=3, q=4; n=5, m=6) { echo hi }'

  _error-case 'proc p (w Int Int) { echo hi }'

  _should-parse 'proc p (w=1, v=2; p Int=3, q List[Int] = [3, 4]; n Int=5, m Int = 6) { echo hi }'

  _should-parse 'proc p (w, ...rest; t, ...rest; named, ...rest; block) { echo hi }'

  _error-case 'proc p ( ; ; ; b1, b2) { echo hi }'
  _error-case 'proc p ( ; ; ; b1, ...rest) { echo hi }'
  _error-case 'proc p ( ; ; ; b1 Str) { echo hi }'

  # Only Command type
  _should-parse 'proc p ( ; ; ; b Command) { echo hi }'

  # bad param
  _error-case 'proc p ( ; ; ; b Command[Int]) { echo hi }'

  _should-parse 'proc p ( ; ; ; ) { echo hi }'
}

test-func-sig() {
  _error-case 'func f { echo hi }'

  _should-parse 'func f () { echo hi }'

  _should-parse 'func f (a List[Int] = [3,4]) { echo hi }'
  _should-parse 'func f (a, b, ...rest; c) { echo hi }'
  _should-parse 'func f (a, b, ...rest; c, ...rest) { echo hi }'
  _error-case 'func f (a, b, ...rest; c, ...rest;) { echo hi }'
}

test-sh-assign() {
  _error-case 'f() { x=y; }'

  # Disallowed in YSH
  _error-case 'proc p { x=y; }'
  _error-case 'func f() { x=y; }'

  return

  # Only proc and func disallow it
  _should-parse '{ x=y; }'
  _should-parse '( x=y; )'

  #_error-case 'func f() { local x=y; }'

  _assert-sh-status 0 $YSH 'Expected it to parse' \
    -o ysh:upgrade -n -c 'x=y'

  # Allowed at the top level
  _should-parse 'x=y echo hi'
  _should-parse 'x=y'

}

test-assign() {
  echo TODO
}

soil-run() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-parse-errors run-test-funcs
}

"$@"

