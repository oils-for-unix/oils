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

_parse-error() {
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

  _parse-error '
  func foo(x) {
    return ()
  }
  '

  _parse-error '
  func foo(x) {
    return (named=x)
  }
  '

  _parse-error '
  func foo(x) {
    return (x, named=x)
  }
  '

  _parse-error '
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

  _parse-error '
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
  _parse-error 'proc p (a Int) { echo hi }'

  _parse-error 'proc p (w, ...) { echo hi }'

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

  _parse-error 'func p (p, ...rest; n, ...rest, z) { echo hi }'
  _parse-error 'func p (p, ...rest; n, ...rest; ) { echo hi }'

  _should-parse 'proc p (w, ...rest; pos, ...rest) { echo hi }'

  _should-parse 'proc p (w, ...rest; pos, ...rest; named=3, ...rest) { echo hi }'

  _should-parse 'proc p (w=1, v=2; p=3, q=4; n=5, m=6) { echo hi }'

  _parse-error 'proc p (w Int Int) { echo hi }'

  _should-parse 'proc p (w=1, v=2; p Int=3, q List[Int] = [3, 4]; n Int=5, m Int = 6) { echo hi }'

  _should-parse 'proc p (w, ...rest; t, ...rest; named, ...rest; block) { echo hi }'

  _parse-error 'proc p ( ; ; ; b1, b2) { echo hi }'
  _parse-error 'proc p ( ; ; ; b1, ...rest) { echo hi }'
  _parse-error 'proc p ( ; ; ; b1 Str) { echo hi }'

  # Only Command type
  _should-parse 'proc p ( ; ; ; b Command) { echo hi }'

  # bad param
  _parse-error 'proc p ( ; ; ; b Command[Int]) { echo hi }'

  _should-parse 'proc p ( ; ; ; ) { echo hi }'
}

test-func-sig() {
  _parse-error 'func f { echo hi }'

  _should-parse 'func f () { echo hi }'

  _should-parse 'func f (a List[Int] = [3,4]) { echo hi }'
  _should-parse 'func f (a, b, ...rest; c) { echo hi }'
  _should-parse 'func f (a, b, ...rest; c, ...rest) { echo hi }'
  _parse-error 'func f (a, b, ...rest; c, ...rest;) { echo hi }'
}

test-sh-assign() {
  _should-parse 'x=y'
  _should-parse 'x=y echo hi'
  _should-parse 'f() { x=y; }'

  # Disallowed in YSH
  _parse-error 'func f() { x=y; }'
  _parse-error 'proc p { x=y; }'

  # Only proc and func disallow it
  _should-parse '{ x=y; }'
  _should-parse '( x=y; )'

  _assert-sh-status 0 $YSH 'Expected it to parse' \
    -o ysh:upgrade -n -c 'x=y'
}

test-ysh-var() {
  set +o errexit

  # Unterminated
  _parse-error 'var x = 1 + '

  _parse-error 'var x = * '

  _parse-error 'var x = @($(cat <<EOF
here doc
EOF
))'

  _parse-error 'var x = $(var x = 1))'
}

test-ysh-expr() {
  set +o errexit
  # old syntax
  _parse-error '= 5 mod 3'

  _parse-error '= >>='
  _parse-error '= %('

  # Singleton tuples
  _parse-error '= 42,'
  _parse-error '= (42,)'

  # Disallowed unconditionally
  _parse-error '=a'

  _parse-error '
    var d = {}
    = d["foo", "bar"]
  '
}

test-ysh-expr-more() {
  # user must choose === or ~==
  _parse-error 'if (5 == 5) { echo yes }'

  _should-parse 'echo $[join(x)]'

  _parse-error 'echo $join(x)'

  _should-parse 'echo @[split(x)]'
  _should-parse 'echo @[split(x)] two'

  _parse-error 'echo @[split(x)]extra'

  # Old syntax to remove
  #_parse-error 'echo @split("a")'
}


test-blocks() {
  _parse-error '>out { echo hi }'
  _parse-error 'a=1 b=2 { echo hi }'
  _parse-error 'break { echo hi }'
  # missing semicolon
  _parse-error 'cd / { echo hi } cd /'
}

test-parse-brace() {
  # missing space
  _parse-error 'if test -f foo{ echo hi }'
}

test-proc-sig() {
  _parse-error 'proc f[] { echo hi }'
  _parse-error 'proc : { echo hi }'
  _parse-error 'proc foo::bar { echo hi }'
}

test-regex-literals() {
  #set +o errexit
  _parse-error 'var x = / ! /'
  _should-parse 'var x = / ![a-z] /'

  _should-parse 'var x = / !d /'

  _parse-error 'var x = / !! /'

  # missing space between rangfes
  _parse-error 'var x = /[a-zA-Z]/'
  _parse-error 'var x = /[a-z0-9]/'

  _parse-error 'var x = /[a-zz]/'

  # can't have multichar ranges
  _parse-error "var x = /['ab'-'z']/"

  # range endpoints must be constants
  _parse-error 'var x = /[$a-${z}]/'

  # These are too long too
  _parse-error 'var x = /[abc]/'

  # Single chars not allowed, should be /['%_']/
  _parse-error 'var x = /[% _]/'

}

test-hay-assign() {
  _parse-error '
name = val
'

  _parse-error '
rule {
  x = 42
}
'

  _parse-error '
RULE {
  x = 42
}
'

  _should-parse '
Rule {
  x = 42
}
'

  _should-parse '
Rule X Y {
  x = 42
}
'

  _should-parse '
RULe {   # inconsistent but OK
  x = 42
}
'

  _parse-error '
hay eval :result {

  Rule {
    foo = 42
  }

  bar = 43   # parse error here
}
'

  _parse-error '
hay define TASK

TASK build {
  foo = 42
}
'

  # CODE node nested inside Attr node.
  _parse-error '
hay define Package/TASK

Package libc {
  TASK build {
    # this is not an attribute, should not be valid
    foo = 42
  }
}
'

  _parse-error '
hay define Rule

Rule {
  return (x)
}
'

  return
  # This is currently allowed, arguably shouldn't be

  _parse-error '
hay define Rule

Rule {
  return 42
}
'
}

test-parse-at() {
  set +o errexit

  _parse-error 'echo @'
  _parse-error 'echo @@'
  _parse-error 'echo @{foo}'
  _parse-error 'echo @/foo/'
  _parse-error 'echo @"foo"'
}

test-ysh-nested-proc() {
  set +o errexit

  _parse-error 'proc p { echo 1; proc f { echo f }; echo 2 }'
  _parse-error 'proc p { echo 1; +weird() { echo f; }; echo 2 }'

  # ksh function
  _parse-error 'proc p { echo 1; function f { echo f; }; echo 2 }'

  _parse-error 'f() { echo 1; proc inner { echo inner; }; echo 2; }'

  # shell nesting is still allowed
  _should-parse 'f() { echo 1; g() { echo g; }; echo 2; }'

  _should-parse 'proc p() { shopt --unset errexit { false hi } }'
}


#
# Entry Points
#

soil-run-py() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

soil-run-cpp() {
  # This is like run-test-funcs, except errexit is off here
  ninja _bin/cxx-asan/osh
  SH=_bin/cxx-asan/osh run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-parse-errors run-test-funcs
}

"$@"

