#!/usr/bin/env bash
#
# Usage:
#   test/ysh-parse-errors.sh <function name>

source test/common.sh
source test/sh-assert.sh  # banner, _assert-sh-status

OSH=${OSH:-bin/osh}
YSH=${YSH:-bin/ysh}

_osh-should-parse() {
  local message="Should parse under $OSH"
  _assert-sh-status 0 $OSH "$message" \
    -n -c "$@"
}

_ysh-should-parse() {
  local message="Should parse under $YSH"
  _assert-sh-status 0 $YSH "$message" \
    -n -c "$@"
}

_ysh-parse-error() {
  local message="Should NOT parse under $YSH"
  _assert-sh-status 2 $YSH "$message" \
    -n -c "$@"
}

#
# Cases
#

test-return-args() {
  set +o errexit

  _ysh-should-parse '
  func foo(x) {
    return (x)
  }
  '

  _ysh-parse-error '
  func foo(x) {
    return ()
  }
  '

  _ysh-parse-error '
  func foo(x) {
    return (named=x)
  }
  '

  _ysh-parse-error '
  func foo(x) {
    return (x, named=x)
  }
  '

  _ysh-parse-error '
  func foo(x) {
    return (x, x)
  }
  '
}

test-func-var-checker() {
  set +o errexit

  _ysh-should-parse '
  func f(x) {
    setvar x = true
  }
  '

  _ysh-parse-error '
  func f() {
    setvar x = true
  }
  '
}

test-arglist() {
  _ysh-parse-error 'json write ()'

  _ysh-should-parse 'p (; n=42)'
  _ysh-should-parse '= f(; n=42)'

  _ysh-parse-error '= f(; 42)'
  _ysh-parse-error '= f(; name)'
  _ysh-parse-error '= f(; x for x in y)'
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
  _ysh-should-parse 'proc p () { echo hi }'
  _ysh-should-parse 'proc p (a) { echo hi }'
  _ysh-should-parse 'proc p (out Ref) { echo hi }'

  # doesn't make sense I think -- they're all strings.  Types don't do any
  # dynamic validation, except 'out Ref' does change semantics
  _ysh-parse-error 'proc p (a Int) { echo hi }'

  _ysh-parse-error 'proc p (w, ...) { echo hi }'

  _ysh-should-parse 'proc p (w, ...rest) { echo hi }'

  # Hm I guess this is fine
  _ysh-should-parse 'proc p (; n Int=3) { echo hi }'

  _ysh-should-parse 'proc p (out Ref; n Int=3) { echo hi }'

  _ysh-should-parse 'proc p (; ; n Int=3) { echo hi }'

  _ysh-should-parse 'proc p ( ; ; ; block) { echo hi }'

  _ysh-should-parse 'proc p (w, ...rest) { echo hi }'
  _ysh-should-parse 'proc p (w, ...rest; t) { echo hi }'

  _ysh-should-parse 'func p (p, ...rest) { echo hi }'

  _ysh-should-parse 'func p (p, ...rest; n, ...named) { echo hi }'
  _ysh-should-parse 'func p (p, ...rest; n, ...named,) { echo hi }'

  _ysh-parse-error 'func p (p, ...rest; n, ...named, z) { echo hi }'
  _ysh-parse-error 'func p (p, ...rest; n, ...named; ) { echo hi }'

  _ysh-should-parse 'proc p (w, ...rest; pos, ...named) { echo hi }'

  _ysh-should-parse 'proc p (w, ...rest; pos, ...args; named=3, ...named) { echo hi }'

  _ysh-should-parse 'proc p (w=1, v=2; p=3, q=4; n=5, m=6) { echo hi }'

  _ysh-parse-error 'proc p (w Int Int) { echo hi }'

  _ysh-should-parse 'proc p (w=1, v=2; p Int=3, q List[Int] = [3, 4]; n Int=5, m Int = 6) { echo hi }'

  _ysh-should-parse 'proc p (w, ...rest; t, ...args; n, ...named; block) { echo hi }'

  _ysh-parse-error 'proc p ( ; ; ; b1, b2) { echo hi }'
  _ysh-parse-error 'proc p ( ; ; ; b1, ...rest) { echo hi }'
  _ysh-parse-error 'proc p ( ; ; ; b1 Str) { echo hi }'

  # Only Command type
  _ysh-should-parse 'proc p ( ; ; ; b Command) { echo hi }'

  # bad param
  _ysh-parse-error 'proc p ( ; ; ; b Command[Int]) { echo hi }'

  _ysh-should-parse 'proc p ( ; ; ; ) { echo hi }'
}

test-proc-def() {
  _ysh-parse-error 'proc p(w) { var w = foo }'
  _ysh-parse-error 'proc p(w; p) { var p = foo }'
  _ysh-parse-error 'proc p(w; p; n, n2) { var n2 = foo }'
  _ysh-parse-error 'proc p(w; p; n, n2; b) { var b = foo }'
}

test-func-sig() {
  _ysh-parse-error 'func f { echo hi }'

  _ysh-should-parse 'func f () { echo hi }'

  _ysh-should-parse 'func f (a List[Int] = [3,4]) { echo hi }'
  _ysh-should-parse 'func f (a, b, ...rest; c) { echo hi }'
  _ysh-should-parse 'func f (a, b, ...rest; c, ...named) { echo hi }'
  _ysh-parse-error 'func f (a, b, ...rest; c, ...named;) { echo hi }'
}

test-func-def() {
  _ysh-parse-error 'func f(p) { var p = foo }'
  _ysh-parse-error 'func f(p; n) { var n = foo }'
}

test-sh-assign() {
  _ysh-should-parse 'x=y'
  _ysh-should-parse 'x=y echo hi'
  _ysh-should-parse 'f() { x=y; }'

  # Disallowed in YSH
  _ysh-parse-error 'func f() { x=y; }'
  _ysh-parse-error 'proc p { x=y; }'

  # Only proc and func disallow it
  _ysh-should-parse '{ x=y; }'
  _ysh-should-parse '( x=y; )'

  _assert-sh-status 0 $YSH 'Expected it to parse' \
    -o ysh:upgrade -n -c 'x=y'
}

test-ysh-var() {
  set +o errexit

  # Unterminated
  _ysh-parse-error 'var x = 1 + '

  _ysh-parse-error 'var x = * '

  _ysh-parse-error 'var x = @($(cat <<EOF
here doc
EOF
))'

  # Hm we need a ; after var or setvar
  _ysh-should-parse 'var x = $(var x = 1; )'
  _ysh-should-parse '
  var x = $(var x = 1
)'
  # This doesn't have it
  _ysh-parse-error 'var x = $(var x = 1)'

  # Extra )
  _ysh-parse-error 'var x = $(var x = 1; ))'
  _ysh-parse-error 'var x = $(var x = 1; ) )'
}

test-ysh-expr() {
  set +o errexit
  # old syntax
  _ysh-parse-error '= 5 mod 3'

  _ysh-parse-error '= >>='
  _ysh-parse-error '= %('

  # Singleton tuples
  _ysh-parse-error '= 42,'
  _ysh-parse-error '= (42,)'

  # Disallowed unconditionally
  _ysh-parse-error '=a'

  _ysh-parse-error '
    var d = {}
    = d["foo", "bar"]
  '
}

test-ysh-expr-more() {
  # user must choose === or ~==
  _ysh-parse-error 'if (5 == 5) { echo yes }'

  _ysh-should-parse 'echo $[join(x)]'

  _ysh-parse-error 'echo $join(x)'

  _ysh-should-parse 'echo @[split(x)]'
  _ysh-should-parse 'echo @[split(x)] two'

  _ysh-parse-error 'echo @[split(x)]extra'

  # Old syntax to remove
  #_ysh-parse-error 'echo @split("a")'
}


test-blocks() {
  _ysh-parse-error '>out { echo hi }'
  _ysh-parse-error 'a=1 b=2 { echo hi }'
  _ysh-parse-error 'break { echo hi }'
  # missing semicolon
  _ysh-parse-error 'cd / { echo hi } cd /'
}

test-parse-brace() {
  # missing space
  _ysh-parse-error 'if test -f foo{ echo hi }'
}

test-proc-sig() {
  _ysh-parse-error 'proc f[] { echo hi }'
  _ysh-parse-error 'proc : { echo hi }'
  _ysh-parse-error 'proc foo::bar { echo hi }'
}

test-regex-literals() {
  #set +o errexit
  _ysh-parse-error 'var x = / ! /'
  _ysh-should-parse 'var x = / ![a-z] /'

  _ysh-should-parse 'var x = / !d /'

  _ysh-parse-error 'var x = / !! /'

  # missing space between rangfes
  _ysh-parse-error 'var x = /[a-zA-Z]/'
  _ysh-parse-error 'var x = /[a-z0-9]/'

  _ysh-parse-error 'var x = /[a-zz]/'

  # can't have multichar ranges
  _ysh-parse-error "var x = /['ab'-'z']/"

  # range endpoints must be constants
  _ysh-parse-error 'var x = /[$a-${z}]/'

  # These are too long too
  _ysh-parse-error 'var x = /[abc]/'

  # Single chars not allowed, should be /['%_']/
  _ysh-parse-error 'var x = /[% _]/'

}

test-hay-assign() {
  _ysh-parse-error '
name = val
'

  _ysh-parse-error '
rule {
  x = 42
}
'

  _ysh-parse-error '
RULE {
  x = 42
}
'

  _ysh-should-parse '
Rule {
  x = 42
}
'

  _ysh-should-parse '
Rule X Y {
  x = 42
}
'

  _ysh-should-parse '
RULe {   # inconsistent but OK
  x = 42
}
'

  _ysh-parse-error '
hay eval :result {

  Rule {
    foo = 42
  }

  bar = 43   # parse error here
}
'

  _ysh-parse-error '
hay define TASK

TASK build {
  foo = 42
}
'

  # CODE node nested inside Attr node.
  _ysh-parse-error '
hay define Package/TASK

Package libc {
  TASK build {
    # this is not an attribute, should not be valid
    foo = 42
  }
}
'

  _ysh-parse-error '
hay define Rule

Rule {
  return (x)
}
'

  return
  # This is currently allowed, arguably shouldn't be

  _ysh-parse-error '
hay define Rule

Rule {
  return 42
}
'
}

test-hay-shell-assign() {
  _ysh-parse-error '
hay define Package

Package foo {
  version=1
}
'

  _ysh-parse-error '
hay define Package/User

Package foo {
  User bob {
    sudo=1
  }
}
'

  _ysh-should-parse '
hay define Package/SHELL/User

Package foo {
  SHELL bob {
    sudo=1
    User {
      name = "z"
    }
  }
}
'

  _ysh-parse-error '
hay define Package/SHELL/User

Package foo {
  SHELL bob {
    # Disallowed
    # a = b
    User {
      x=1
    }
  }
}
'

  return

  # It's OK that this parses, we didn't use the CapsWord style

  _ysh-parse-error '
hay define package user TASK

hay eval :result {
  package foo {
    version=1
  }
}
'
}

test-parse-at() {
  set +o errexit

  _ysh-parse-error 'echo @'
  _ysh-parse-error 'echo @@'
  _ysh-parse-error 'echo @{foo}'
  _ysh-parse-error 'echo @/foo/'
  _ysh-parse-error 'echo @"foo"'
}

test-ysh-nested-proc-func() {
  set +o errexit

  _ysh-parse-error 'proc p { echo 1; proc f { echo f }; echo 2 }'
  _ysh-parse-error 'func f() { echo 1; proc f { echo f }; echo 2 }'
  _ysh-parse-error 'proc p { echo 1; func f() { echo f }; echo 2 }'
  _ysh-parse-error 'func f() { echo 1; func f2() { echo f }; echo 2 }'

  _ysh-parse-error 'proc p { echo 1; +weird() { echo f; }; echo 2 }'

  # ksh function
  _ysh-parse-error 'proc p { echo 1; function f { echo f; }; echo 2 }'

  _ysh-parse-error 'f() { echo 1; proc inner { echo inner; }; echo 2; }'

  # shell nesting is still allowed
  _ysh-should-parse 'f() { echo 1; g() { echo g; }; echo 2; }'

  _ysh-should-parse 'proc p() { shopt --unset errexit { false hi } }'
}

test-int-literals() {
  _ysh-should-parse '= 42'
  _ysh-should-parse '= 42_0'
  _ysh-parse-error '= 42_'
  _ysh-parse-error '= 42_0_'

  # this is a var name
  _ysh-should-parse '= _42'
}

test-float-literals() {
  _ysh-should-parse '= 42.0'
  _ysh-should-parse '= 42_0.0'
  _ysh-parse-error '= 42_.0'

  _ysh-parse-error '= 42.'
  _ysh-parse-error '= .333'

  _ysh-parse-error '= _42.0'
}

test-place-expr() {
  _ysh-should-parse 'setvar x.y = 42'
  _ysh-parse-error 'setvar x+y = 42'
  _ysh-parse-error 'setvar x->y = 42'
}

test-destructure() {
  _ysh-parse-error '
  func f() {
    const x, y = 3, 4

    #setvar x = 5

    setvar y = 6
  }'

  _ysh-parse-error '
  func f() {
    var x, y = 3, 4

    var y = 6
  }'

  _ysh-parse-error '
  func f() {
    var x, y = 3, 4

    const y = 6
  }'
}

test-lazy-arg-list() {
  _ysh-should-parse 'assert [42 === x]'

  _ysh-should-parse 'assert [ 42 === x ]'
  _ysh-should-parse 'assert [42, 43]'
  _ysh-should-parse 'assert [42, named=true]'
  _ysh-should-parse 'assert [42, named=true]; echo hi'

  _ysh-should-parse 'assert [42, named=true] { echo hi }'

  # Seems fine
  _ysh-should-parse 'assert [42, named=true]{ echo hi }'

  # I guess this legacy is still valid?  Or disallow explicitly
  _ysh-should-parse 'assert *.[ch]'
  _ysh-should-parse 'assert 42[ch]'
  _ysh-should-parse 'echo[]'

  _ysh-parse-error 'assert [4'
  _ysh-parse-error 'assert [ 4'

  _ysh-should-parse 'json write (42) >out'

  # I guess this is OK
  _ysh-should-parse 'json write >out (42)'

  # BUG
  #_ysh-parse-error 'when (42) >out { echo hi }'

  #_ysh-should-parse 'when (42) { echo hi } >out'

  # How to support this?  Maybe the CommandParser can test for i == 0 when it
  # gets Op_LBracket

  # legacy
  _ysh-should-parse '[ x = y ]'


  return

  # TODO: shouldn't allow extra words
  _ysh-parse-error 'assert (42)extra'
  _ysh-parse-error 'assert (42) extra'


  _ysh-parse-error 'assert [42]extra'
  _ysh-parse-error 'assert [42] extra'
}

test-place-expr() {
  _ysh-should-parse 'read (&x)'

  # TODO: parse these into something
  _ysh-parse-error 'read (&x[0])'
  _ysh-parse-error 'read (&x[0][1])'

  _ysh-parse-error 'read (&x.key.other)'

  # This is a runtime error, not a parse time error
  _ysh-should-parse 'read (&x + 1)'

  _ysh-parse-error 'read (&42)'
  _ysh-parse-error 'read (&+)'

  # Place expressions aren't parenthesized expressions
  _ysh-parse-error 'read (&(x))'
}

test-units-suffix() {
  _ysh-parse-error '= 100 M M'

  _ysh-parse-error '= 100 M; echo'
  _ysh-parse-error '= 100 Mi; echo'

  _ysh-parse-error '= 9.9 Mi; echo'

  # This is confusing, could disallow, or just rely on users not to type it
  _ysh-parse-error '= 9.9e-1 Mi; echo'

  # I don't like this, but it follows lexing rules I guess
  _ysh-parse-error '= 100Mi'

  _ysh-parse-error '= [100 Mi, 200 Mi]'

  _ysh-parse-error '= {[42 Ki]: 43 Ki}'
}

test-type-expr() {
  # This is nicer
  _ysh-should-parse 'var x: Int = f()'

  # But colon is optional
  _ysh-should-parse 'var x Int = f()'

  # Colon is noisy here because we have semi-colons
  _ysh-should-parse 'proc p (; x Int, y Int; ) { echo hi }'

  _ysh-should-parse 'func f (x Int, y Int; z Int = 0) { echo hi }'

  # Hm should these be allowed, but discouraged?
  #_ysh-should-parse 'func f (x Int, y Int; z: Int = 0) { echo hi }'
  #_ysh-should-parse 'proc p (; x: Int, y: Int;) { echo hi }'
}

test-no-const() {
  _ysh-should-parse 'const x = 42'

  # Must be at the top level
  _ysh-parse-error '
  proc p {
    const x = 42
  }'

  _ysh-parse-error '
  func f() {
    const x = 42
  }'
}

test-fat-arrow() {
  _ysh-should-parse 'var x = s => trim()'
  _ysh-should-parse 'func f(x Int) => List[Int] { echo hi }'
}

# Backslash in UNQUOTED context
test-parse-backslash() {
  set +o errexit

  _ysh-should-parse 'echo \('
  _ysh-should-parse 'echo \;'
  _ysh-should-parse 'echo ~'
  _ysh-should-parse 'echo \!'  # history?

  _ysh-should-parse 'echo \%'  # job ID?  I feel like '%' is better
  _ysh-should-parse 'echo \#'  # comment

  _ysh-parse-error 'echo \.'
  _ysh-parse-error 'echo \-'
  _ysh-parse-error 'echo \/'

  _ysh-parse-error 'echo \a'
  _ysh-parse-error 'echo \Z'
  _ysh-parse-error 'echo \0'
  _ysh-parse-error 'echo \9'

  _osh-should-parse 'echo \. \- \/ \a \Z \0 \9'
}

test-make-these-nicer() {
  set +o errexit

  # expects expression on right
  _ysh-parse-error '='
  _ysh-parse-error 'call'

  # What about \u{123} parse errors
  # I get a warning now, but parse_backslash should give a syntax error
  # _ysh-parse-error "x = c'\\uz'"

  # Dict pair split
  _ysh-parse-error 'const d = { name:
42 }'

  #_ysh-parse-error ' d = %{}'
}

test-var-decl() {
  set +o errexit

  _ysh-parse-error '
  proc p(x) {
    echo hi
    var x = 2  # Cannot redeclare param
  }
  '

  _ysh-parse-error '
  proc p {
    var x = 1
    echo hi
    var x = 2  # Cannot redeclare local
  }
  '

  _ysh-parse-error '
  proc p(x, :out) {
    var out = 2   # Cannot redeclare out param
  }
  '

  _ysh-parse-error '
  proc p {
    var out = 2   # Cannot redeclare out param
    cd /tmp { 
      var out = 3
    }
  }
  '

  _ysh-should-parse '
  var x = 1
  proc p {
    echo hi
    var x = 2
  }

  proc p2 {
    var x = 3
  }
  '
}

test-setvar() {
  set +o errexit

  _ysh-should-parse '
  proc p(x) {
    var y = 1
    setvar y = 42
  }
  '

  _ysh-parse-error '
  proc p(x) {
    var y = 1
    setvar L = "L"  # ERROR: not declared
  }
  '

  _ysh-parse-error '
  proc p(x) {
    var y = 1
    setvar L[0] = "L"  # ERROR: not declared
  }
  '

  _ysh-parse-error '
  proc p(x) {
    var y = 1
    setvar d.key = "v"  # ERROR: not declared
  }
  '

  _ysh-should-parse '
  proc p(x) {
    setvar x = "X"  # is mutating params allowed?  I guess why not.
  }
  '
}

test-ysh-case() {
  set +o errexit

  _ysh-should-parse '
  case (x) {
    (else) { = 1; }
  }
  '

  _ysh-should-parse '
  var myexpr = ^[123]

  case (123) {
    (myexpr) { echo 1 }
  }
  '

  _ysh-should-parse '
  case (x) {
    (else) { echo 1 }
  }
  '

  _ysh-should-parse '
  case (x) {
    (else) { = 1 }
  }
  '

  _ysh-should-parse '
  case (x) {
    (else) { = 1 } 
 
  }
  '

  _ysh-should-parse '
  case (x) {
    (else) { = 1 }  # Comment
  }
  '

  _ysh-should-parse '
  case (3) {
    (3) { echo hi }
    # comment line
  }
  '

  _ysh-should-parse '
  case (x) {
    (else) { echo 1 } 
  }
  '

  _ysh-should-parse '
  case (foo) { (else) { echo } }
  '

  _ysh-should-parse '
  case (foo) {
    *.py { echo "python" }
  }
  '

  _ysh-should-parse '
  case (foo) {
    (obj.attr) { echo "python" }
  }
  '

  _ysh-should-parse '
  case (foo) {
    (0) { echo "python" }
  }
  '

  _ysh-should-parse '
  case (foo) {
    ("main.py") { echo "python" }
  }
  '

  # Various multi-line cases
  if false; then # TODO: fixme, this is in the vein of the `if(x)` error
    _ysh-should-parse '
    case (foo){("main.py"){ echo "python" } }
    '
  fi
  _ysh-should-parse '
  case (foo) { ("main.py") { echo "python" } }
  '
  _ysh-should-parse '
  case (foo) {
    ("main.py") {
      echo "python" } }'
  _ysh-should-parse '
  case (foo) {
    ("main.py") {
      echo "python" }
  }
  '
  _ysh-should-parse '
  case (foo) {
    ("main.py") { echo "python"
    }
  }
  '
  _ysh-should-parse '
  case (foo) {
    ("main.py") {
      echo "python"
    }
  }
  '

  # Example valid cases from grammar brain-storming
  _ysh-should-parse '
  case (add(10, 32)) {
    (40 + 2) { echo Found the answer }
    (else) { echo Incorrect
    }
  }
  '

  _ysh-should-parse "
  case (file) {
    / dot* '.py' / {
      echo Python
    }

    / dot* ('.cc' | '.h') /
    {
      echo C++
    }
  }
  "
  _ysh-should-parse '
  case (lang) {
      en-US
    | en-CA
    | en-UK {
      echo Hello
    }
    fr-FR |
    fr-CA {
      echo Bonjour
    }





    (else) {
      echo o/
    }
  }
  '

  _ysh-should-parse '
  case (num) {
    (1) | (2) {
      echo number
    }
  }
  '

  _ysh-should-parse '
  case (num) {
      (1) | (2) | (3)
    | (4) | (5) {
      echo small
    }

    (else) {
      echo large
    }
  }
  '

  # Example invalid cases from grammar brain-storming
  _ysh-parse-error '
  case
  (add(10, 32)) {
      (40 + 2) { echo Found the answer }
      (else) { echo Incorrect }
  }
  '
  _ysh-parse-error "
  case (file)
  {
    ('README') | / dot* '.md' / { echo Markdown }
  }
  "
  _ysh-parse-error '
  case (file)
  {
    {
      echo Python
    }
  }
  '
  _ysh-parse-error '
  case (file)
  {
    cc h {
      echo C++
    }
  }
  '
  _ysh-parse-error "
  case (lang) {
      en-US
    | ('en-CA')
    | / 'en-UK' / {
      echo Hello
    }
  }
  "
  _ysh-parse-error '
  case (lang) {
    else) {
      echo o/
    }
  }
  '
  _ysh-parse-error '
  case (num) {
      (1) | (2) | (3)
    | (4) | (5) {
      echo small
    }

    (6) | (else) {
      echo large
    }
  }
  '

  _ysh-parse-error '
  case $foo {
    ("main.py") {
      echo "python"
    }
  }
  '

  # Newline not allowed, because it isn't in for, if, while, etc.
  _ysh-parse-error '
  case (x)
  {
    *.py { echo "python" }
  }
  '

  _ysh-parse-error '
  case (foo) in
    *.py {
      echo "python"
    }
  esac
  '

  _ysh-parse-error '
  case $foo {
    bar) {
      echo "python"
    }
  }
  '

  _ysh-parse-error '
  case (x) {
    {
      echo "python"
    }
  }
  '

  _ysh-parse-error '
  case (x {
    *.py { echo "python" }
  }
  '

  _ysh-parse-error '
  case (x) {
    *.py) { echo "python" }
  }
  '

  _ysh-should-parse "case (x) { word { echo word; } (3) { echo expr; } /'eggex'/ { echo eggex; } }"

  _ysh-should-parse "
case (x) {
  word    { echo word; } (3)     { echo expr; } /'eggex'/ { echo eggex; } }"

  _ysh-should-parse "
case (x) {
  word    { echo word; }
  (3)     { echo expr; } /'eggex'/ { echo eggex; } }"

  _ysh-should-parse "
case (x) {
  word    { echo word; }
  (3)     { echo expr; }
  /'eggex'/ { echo eggex; } }"

  _ysh-should-parse "
case (x) {
  word    { echo word; }
  (3)     { echo expr; }
  /'eggex'/ { echo eggex; }
}"

  # No leading space
  _ysh-should-parse "
case (x) {
word    { echo word; }
(3)     { echo expr; }
/'eggex'/ { echo eggex; }
}"
}

test-ysh-for() {
  set +o errexit

  _ysh-should-parse '
  for x in (obj) {
    echo $x
  }
  '

  _ysh-parse-error '
  for x in (obj); do
    echo $x
  done
  '

  _ysh-should-parse '
  for x, y in SPAM EGGS; do
    echo $x
  done
  '

  # Bad loop variable name
  _ysh-parse-error '
  for x-y in SPAM EGGS; do
    echo $x
  done
  '

  # Too many indices
  _ysh-parse-error '
  for x, y, z in SPAM EGGS; do
    echo $x
  done
  '

  _ysh-parse-error '
  for w, x, y, z in SPAM EGGS; do
    echo $x
  done
  '

  # Old style
  _ysh-should-parse '
  for x, y in SPAM EGGS
  do
    echo $x
  done
  '

  # for shell compatibility, allow this
  _ysh-should-parse 'for const in (x) { echo $var }'
}

test-for-parse-bare-word() {
  set +o errexit

  _ysh-parse-error '
  for x in bare {
    echo $x
  }
  '

  _ysh-should-parse '
  for x in a b {
    echo $x
  }
  '

  _ysh-should-parse '
  for x in *.py {
    echo $x
  }
  '

  _ysh-should-parse '
  for x in "quoted" {
    echo $x
  }
  '
}

test-bug-1118() {
  set +o errexit

  # Originally pointed at 'for'
  _ysh-parse-error '
  var snippets = [{status: 42}]
  for snippet in (snippets) {
    if (snippet["status"] === 0) {
      echo hi
    }

    # The $ causes a weird error
    if ($snippet["status"] === 0) {
      echo hi
    }
  }
  '

  # Issue #1118
  # pointed at 'var' in count
  _ysh-parse-error '
  var content = [ 1, 2, 4 ]
  var count = 0

  # The $ causes a weird error
  while (count < $len(content)) {
    setvar count += 1
  }
  '
}

test-bug-1850() {
  _ysh-should-parse 'pp line (42); pp line (43)'
  #_osh-should-parse 'pp line (42); pp line (43)'

  return

  # Extra word is bad
  _ysh-parse-error 'pp line (42) extra'

  # Bug -- newline or block should come after arg list
  _ysh-parse-error 'pp line (42), echo'

  # This properly checks a similar error.  It's in a word.
  _ysh-parse-error 'pp line @(echo), echo'

  # Common cases
  _ysh-should-parse 'pp line (42)'
  _ysh-should-parse 'pp line (42) '
  _ysh-should-parse 'pp line (42);'
  _ysh-should-parse 'pp line (42) { echo hi }'

  return

  # Original bug

  # Accidental comma instead of ;
  # Wow this is parsed horribly
  # Why does this replace (42) with (43)
  _ysh-parse-error 'pp line (42), pp line (43)'
}

test-proc-args() {
  set +o errexit

  _osh-should-parse 'json write (x)'

  _osh-should-parse 'echo $(json write (x))'  # relies on lexer.PushHint()

  # nested expr -> command -> expr
  _osh-should-parse 'var result = $(json write (x))'

  _osh-should-parse 'json write (x, y); echo hi'

  # named arg
  _osh-should-parse '
json write (x, name = "value")
echo hi
'

  # with block on same line
  _ysh-should-parse 'json write (x) { echo hi }'

  # with block
  _ysh-should-parse '
json write (x) {
  echo hi
}'

  # multiple lines
  _osh-should-parse 'json write (
    x,
    y,
    z
  )'

  # can't be empty
  _ysh-parse-error 'json write ()'
  _ysh-parse-error 'json write ( )'

  # should have a space
  _ysh-parse-error 'json write(x)'
  _ysh-parse-error 'json write()'
  _ysh-parse-error 'f(x)'  # test short name
}

test-eggex-capture() {
  _ysh-should-parse '= / d+ /'
  #_ysh-should-parse '= / <d+ : date> /'
  _ysh-should-parse '= / < capture d+ as date > /'
  _ysh-should-parse '= / < capture d+ as date: Int > /'

  # These keywords are taken in regular expressions, I guess that's OK.
  _ysh-parse-error 'var capture = 42'
  _ysh-parse-error 'var as = 42'
}


test-eggex-flags() {
  _ysh-should-parse '= / d+ ; reg_icase /'
  _ysh-should-parse '= / d+ ; i /'  # shortcut

  # can't negate these
  _ysh-parse-error '= / d+ ; !i /'

  # typo should be parse error
  _ysh-parse-error '= / d+ ; reg_oops /'

  # PCRE should not validate
  _ysh-should-parse '= / d+ ; !i; PCRE /'
  _ysh-should-parse '= / d+ ; reg_oops; PCRE /'

  # ERE means is the default; it's POSIX ERE
  # Other option is PCRE
  _ysh-should-parse '= / d+ ; i reg_newline ; ERE /'
  _ysh-should-parse '= / d+ ; ; ERE /'

  # trailing ; is OK
  _ysh-should-parse '= / d+ ; /'

  # doesn't make sense
  _ysh-parse-error '= / d+ ; ; /'
  _ysh-parse-error '= / d+ ; ; ; /'
}

test-string-literals() {
  _ysh-should-parse "echo r'hi';"
  #_ysh-parse-error "echo r'hi'bad"

  _ysh-should-parse "echo u'hi'"
  _ysh-should-parse "(echo u'hi')"

  _ysh-parse-error "echo b'hi'trailing"
  _ysh-parse-error "echo b'hi'#notcomment"

  # This is valid shell, but not a comment
  _ysh-should-parse "echo 'hi'#notcomment"

}

test-multiline-string() {
  _ysh-should-parse "echo u'''
hi
'''
"
  _ysh-should-parse "echo b'''
hi
'''
"

  _ysh-parse-error "echo b'''
hi
''
"

  _ysh-parse-error "echo r'''
hi
'''bad
"

  _ysh-parse-error "echo u'''
hi
'''bad
"

  _ysh-parse-error 'echo """
hi
"""bad
'
}

test-bug-1826() {
  #return

  read -r code_str << 'EOF'
echo b'\xff'
EOF

  _ysh-parse-error "$code_str"

  read -r code_str << 'EOF'
var s = b'\xff'
EOF

  _ysh-parse-error "$code_str"

  # Backslash ending the file

  read -r code_str << 'EOF'
echo b'\
EOF
  echo "[$code_str]"

  _ysh-parse-error "$code_str"

  read -r code_str << 'EOF'
var s = b'\
EOF
  echo "[$code_str]"

  _ysh-parse-error "$code_str"

  read -r code_str << 'EOF'
var s = $'\
EOF
  echo "[$code_str]"

  _ysh-parse-error "$code_str"
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

