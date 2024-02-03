#!/usr/bin/env bash
#
# Usage:
#   test/ysh-runtime-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh
source test/sh-assert.sh  # banner, _assert-sh-status

YSH=${YSH:-bin/ysh}

#
# Assertions
#

_osh-error-case-X() {
  local expected_status=$1
  shift

  local message=$0
  _assert-sh-status $expected_status $OSH "$message" \
    -c "$@"
}

_error-case-X() {
  local expected_status=$1
  shift

  local message=$0
  _assert-sh-status $expected_status $YSH "$message" \
    -c "$@"
}

_error-case() {
  ### Expect status 1
  _error-case-X 1 "$@"
}

_expr-error-case() {
  ### Expect status 3
  _error-case-X 3 "$@"
}

_should-run() {
  local message='Should run under YSH'
  _assert-sh-status 0 $YSH "$message" \
    -c "$@"
}

#
# Cases
#

test-no-typed-args() {
  # Hm these could both be J8 notation
  #_error-case 'echo (42)'
  #_error-case 'write (42)'

  _error-case-X 2 'true (42)'
  _error-case-X 2 'false { echo hi }'
}

test-undefined-vars() {
  set +o errexit

  _error-case 'echo hi; const y = 2 + x + 3'
  _error-case 'if (x) { echo hello }'
  _error-case 'if (${x}) { echo hi }'

  # BareDecl and regex
  _error-case 'const x = / @undef /; echo hi'

  _error-case 'var x = undef; echo $x'  # VarDecl
  _error-case 'setvar a = undef'  # PlaceMutation
}

test-word-eval-with-ysh-data() {
  set +o errexit

  _expr-error-case 'var d = {}; echo ${d:-}'

  _osh-error-case-X 3 'var d = {}; echo ${#d}'

  _osh-error-case-X 3 'var d = {}; echo ${d[0]}'

  _osh-error-case-X 3 'var d = {}; echo ${d[@]:1:3}'

  _osh-error-case-X 3 'var d = {}; echo ${!d}'

  _osh-error-case-X 3 'var d = {}; echo ${!d[@]}'

  _osh-error-case-X 3 'var d = {}; echo ${d#prefix}'

  _osh-error-case-X 3 'var d = {}; echo ${d//a/b}'

}

test-ysh-word-eval() {
  set +o errexit

  # Wrong sigil
  _expr-error-case 'echo $[maybe("foo")]'

  # Wrong sigil
  _expr-error-case 'source --builtin funcs.ysh; echo $[identity({key: "val"})]'

  # this should be consistent
  _expr-error-case 'source --builtin funcs.ysh; write -- @[identity([{key: "val"}])]'

  _expr-error-case 'const x = [1, 2]; echo $x'

  _should-run 'var x = [1, 2]; write @x'

  # errors in items
  _expr-error-case 'var x = [3, {}]; write @x'

  _expr-error-case 'var x = [3, {}]; write @[x]'

  # errors at top level
  _expr-error-case 'var x = /d+/; write @x'

  _expr-error-case 'var x = /d+/; write @[x]'
}

test-ysh-expr-eval() {
  set +o errexit

  _expr-error-case 'echo $[42 / 0 ]'

  _expr-error-case 'var d = {}; var item = d->nonexistent'

  _expr-error-case 'var d = {}; var item = d["nonexistent"]'

  _expr-error-case 'var a = []; setvar item = a[1]'

  _expr-error-case 'const x = 42 / 0'

  # command sub as part of expression retains its exit code
  _error-case 'var x = "z" ++ $(false)'
  #_error-case 'var x = "z" ++ $(exit 42)'

  _expr-error-case 'case (42 / 0) { * { echo hi } }; echo OK'

  _expr-error-case 'var d = {}; for x in $[d->zzz] { echo hi }'

  # Wrong index type
  _expr-error-case 'var d = {}; setvar d[42] = 3'
  _expr-error-case 'var L = []; setvar L["key"] = 3'

}

test-ysh-expr-eval-2() {
  _expr-error-case 'var L = []; var slice = L["foo": "bar"]'

  _expr-error-case '= 3 < true'
  _expr-error-case '= "a" < "b"'

  _expr-error-case 'var key = 42; var d = {[key]: 3}'

  _expr-error-case 'var d = {}; var a = d.a'
  _expr-error-case 'var d = []; var a = d.a'

  _expr-error-case '= 3 ** -2'
  _expr-error-case '= 3.2 ** 2'

  _expr-error-case '= - "foo"'
}

test-user-reported() {
  set +o errexit

  #_error-case 'echo'

  # Issue #1118
  # Some tests became test/parse-errors.sh


  # len(INTEGER) causes the same problem
  _expr-error-case '
  var snippets = [{status: 42}]
  for snippet in (snippets) {
    if (len(42)) {
      echo hi
    }
  }
  '

  # len(INTEGER) causes the same problem
  _expr-error-case '
  var count = 0

  # The $ causes a weird error
  while (count < len(count)) {
    setvar count += 1
  }
  '
}

test-fallback-locations() {
  # Melvin noticed bug here
  _expr-error-case 'if (len(42)) { echo hi }'

  # Be even more specific
  _expr-error-case 'if (1 + len(42)) { echo hi }'

  # From Aidan's PR -- redefinition
  _error-case 'const f = 42; func f() { echo hi }'

  # ForEach shell
  _expr-error-case 'for x in $[2 + len(42)] { echo hi }'

  # ForEach YSH
  _expr-error-case 'for x in (len(42)) { echo hi }'

  _expr-error-case 'while (len(42)) { echo hi }'

  _expr-error-case 'case (len(42)) { pat { echo argument } }'
  _expr-error-case 'case (42) { (len(42)) { echo arm } }'

  _expr-error-case 'case "$[len(42)]" in pat) echo hi ;; esac'

  _expr-error-case 'var x = 3 + len(42)'
  _expr-error-case 'const x = 3 + len(42)'
  _expr-error-case 'setvar x = 3 + len(42)'

  _expr-error-case 'setvar x = "s" + 5'
  _expr-error-case 'while ("s" + 5) { echo yes } '

  #_expr-error-case 'func f(x) { return (x) }; var x = f([1,2])(3); echo $x'

  # Really bad one
  _expr-error-case 'func f(x) { return (x) }; var x = f([1,2])[1](3); echo $x'
}

test-EvalExpr-calls() {
  ### Test everywhere expr_ev.EvalExpr() is invoked

  _expr-error-case 'json write (len(42))'

  _expr-error-case '= len(42)'
  _expr-error-case 'call len(42)'

  _expr-error-case 'echo $[len(42)]'
  _expr-error-case 'echo $[len(z = 42)]'

  _expr-error-case 'echo @[len(42)]'
  _expr-error-case 'echo @[len(z = 42)]'

  _expr-error-case 'const x = len(42)'
  _expr-error-case 'setvar x += len(42)'

  _expr-error-case '
    var d = {}
    setvar d[len(42)] = "foo"
  '

  _expr-error-case '
    var d = {}
    setvar len(42).z = "foo"
  '

  _expr-error-case '
  hay define Package
  Package foo {
    x = len(42)
  }
  '

  _expr-error-case 'if (len(42)) { echo hi }'

  _expr-error-case 'while (len(42)) { echo hi }'

  _expr-error-case 'for x in (len(42)) { echo $x }'

}


test-hay() {
  _error-case-X 127 '
hay define package user TASK

hay eval :result {
  package foo {
    # commands can be run while evaluating
    oops
  }

  bad 2
}
'
}


test-hay-osh() {
   # forgot parse_brace
  _osh-error-case-X 2 '
hay define package TASK

package foo {
  version = 1
}
'

   # forgot parse_equals
  _osh-error-case-X 127 '
shopt --set parse_brace

hay define package TASK

hay eval :result {
  package foo {
    version = 1
  }
}
'
}

test-eggex() {
   # forgot parse_brace
  _should-run ' = / [ \x00 \xff ] /'
  _should-run ' = / [ \x00-\xff ] /'

  # Shouldn't be in strings

  cat >_tmp/test-eggex.txt <<'EOF'
= / [ $'\x00 \xff' ] /
EOF

  _error-case "$(cat _tmp/test-eggex.txt)"

  _should-run ' = / [ \u{0} ] /'
  _should-run ' = / [ \u{0}-\u{1} ] /'

  # Too high
  _error-case 'var x =/ [ \u{80} ] /; echo $x'
  _error-case 'var x = / [ \u{7f}-\u{80} ] /; echo $x'

  # Now test special characters
  _should-run "$(cat <<'EOF'
= / [ \\ '^-]' 'abc' ] /
EOF
)"

  # Special chars in ranges are disallowed for simplicity
  _error-case "var x = / [ a-'^' ] /; echo \$x"
  _error-case "var x = / [ '-'-z ] /; echo \$x"
  _error-case "var x = / [ ']'-z ] /; echo \$x"

  # TODO: Disallow this.  It translates to [^], which is a syntax error in
  # egrep "Unmatched [ or [^"
  _should-run "var x = / ['^'] /; echo \$x"

  _expr-error-case '
  var i = 42
  = / @i /   # splice object of wrong type
  '

  _expr-error-case '
  var i = 42
  = / [a @i] /   # char class splice object of wrong type
  '
}

test-eggex-2() {
  set +o errexit

  _should-run "var sq = / 'foo'+ /"

  _should-run "$(cat <<'EOF'
  var sq = / ('foo')+ /
  echo $sq

  var sq2 = / <capture 'foo'>+ /
  echo $sq2
EOF
)"

  _error-case '
  var literal = "foo"
  var svs = / @literal+ /
  echo $svs
  '
}

test-eggex-api() {
  _expr-error-case '= _group(0)'  # No groups

  _expr-error-case 'if ("foo" ~ /[a-z]/) { echo $[_group(1)] }'
  _expr-error-case 'if ("foo" ~ /[a-z]/) { echo $[_group("name")] }'

  # ERE
  _expr-error-case 'if ("foo" ~ "[a-z]") { echo $[_group(1)] }'
  _expr-error-case 'if ("foo" ~ "[a-z]") { echo $[_group("name")] }'

  _expr-error-case '= _group("foo")'  # No such group
}

test-eggex-convert-func() {

  _should-run '= / <capture d+ as month: int> /'
  _should-run '= / <capture d+: int> /'
  _should-run '= / <capture d+> /'

  # bad convert func
  _expr-error-case '= / <capture d+ as month: BAD> /'
  _expr-error-case '= / <capture d+: BAD> /'

  # type error calling convert func (evalExpr)
  _expr-error-case 'var pat = / <capture d+: evalExpr> /; var m = "10" => search(pat) => group(1)'
}

test-int-convert() {
  _expr-error-case '= int({})'
  _expr-error-case '= int([])'
  _expr-error-case '= int("foo")'
  _expr-error-case '= int(len)'
  _expr-error-case '= int("foo"->startswith)'
}

test-float-convert() {
  _expr-error-case '= float({})'
  _expr-error-case '= float([])'
  _expr-error-case '= float("foo")'
  _expr-error-case '= float(len)'
  _expr-error-case '= float("foo"->startswith)'
}

test-str-convert() {
  _expr-error-case '= str({})'
  _expr-error-case '= str([])'
  _expr-error-case '= str(len)'
  _expr-error-case '= str("foo"->startswith)'
}

test-list-convert() {
  _expr-error-case '= list(1)'
  _expr-error-case '= list(len)'
  _expr-error-case '= list("foo"->startswith)'
}

test-dict-convert() {
  _expr-error-case '= dict(1)'
  _expr-error-case '= dict("foo")'
  _expr-error-case '= dict(len)'
  _expr-error-case '= dict("foo"->startswith)'
  _expr-error-case '= dict([["too", "many", "parts"]])'
}

test-proc-error-locs() {

  # positional
  _expr-error-case '
  var d = [1]

  func f(a=1, x=d[2]) {
    echo hi
  }
  '

  _expr-error-case '
  var d = [1]

  func f(; n=1, m=d[2]) {
    echo hi
  }
  '
}

test-func-error-locs() {
  # free funcs
  _expr-error-case '= join(["foo", "bar"], " ", 99)' # too many args
  _expr-error-case '= int()' # not enough args
  _expr-error-case '= str({})' # wrong type

  # bound funcs
  _expr-error-case '= "foo"->startswith("f", "o")' # too many args
  _expr-error-case '= "foo"->startswith()' # not enough args
  _expr-error-case '= "foo"->startswith(1)' # wrong type

  _expr-error-case '
  func f(x) {
     return (x)
  }
  = f()
  '
}

test-var-decl() {
  _expr-error-case 'var x, y = 1, 2, 3'
  _expr-error-case 'setvar x, y = 1, 2, 3'
}

test-proc-defaults() {
  
  # should be string
  _expr-error-case 'proc p(word=42) { echo }'
  _expr-error-case 'proc p(word=null) { echo }'

  # should be ^() or null
  _expr-error-case 'proc p( ; ; ; block="str") { echo }'
  _expr-error-case 'proc p( ; ; ; block=[]) { echo }'

  _should-run 'proc p( ; ; ; block=^(echo hi)) { true }'
  _should-run 'proc p( ; ; ; block=null) { true }'

  # divide by zero
  _expr-error-case 'proc p(word; t=42/0) { echo }'

  _error-case-X 1 'proc p(word; t=f()) { echo }'

  _error-case-X 1 'proc p(word; t=42; named=undef) { echo }'

  _error-case-X 1 'proc p(word; t=42; named=43; block=ZZ) { echo }'

  _should-run '
  proc p(word="yo"; t=42; named=43; block=null) {
    #echo $word $t $named $block
    echo $word $t $block
  }
  p
  '
}

test-proc-passing() {
  # Too few words
  _error-case-X 3 '
  proc p(a, b) { echo }
  p a
  '

  # Too many words
  _error-case-X 3 '
  proc p(a, b) { echo }
  p AA b c DD
  '

  # Too few typed
  _error-case-X 3 '
  proc p( ; a, b) { echo }
  p (42)
  '

  # Too many words
  _error-case-X 3 '
  proc p( ; a, b) { echo }
  p (42, 43, 44, 45)
  '

  _expr-error-case '
  proc p(; a, b) {
    echo $a - $b -
  }
  p (...[1, 2])
  p (...3)
  '

  # positional: rest args and spread
  _should-run '
  proc p(; a, ...b) {
    echo $a - @b -
  }
  p (1, 2, 3)

  var x = [4, 5, 6]
  p (...x)
  '

  # named: splat
  _should-run '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  var kwargs = {a: 42, b: 43}
  myproc (99; ...kwargs)
  '

  # named: rest args
  _should-run '
  proc myproc (; p ; a, b, ...named) {
    = p
    = a
    = b
    = named
  }
  var kwargs = {a: 42, b: 43, c:44}
  myproc (99; ...kwargs)
  '
}

# TODO: improve locations for all of these
test-proc-missing() {
  # missing word param
  _error-case-X 3 '
  proc myproc (w) {
    = w
  }
  myproc
  '

  # missing typed param
  _error-case-X 3 '
  proc myproc (w; t1, t2) {
    = w
    = t
  }
  myproc foo (42)
  '

  # missing named param
  _error-case-X 3 '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  myproc (99, b=3)
  '

  # missing named param with semicolon
  _error-case-X 3 '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  myproc (99; b=3)
  '

  # missing block param
  _error-case-X 3 '
  proc myproc (w; p ; a, b; block) {
    = block
  }
  myproc foo (99, a=1, b=2)
  '
}

test-proc-extra() {

  # extra word
  _error-case-X 3 '
  proc myproc () {
    echo hi
  }
  myproc foo
  '

  # extra positional
  _error-case-X 3 '
  proc myproc (w) {
    echo hi
  }
  myproc foo (42)
  '

  # extra named
  _error-case-X 3 '
  proc myproc (w; p) {
    echo hi
  }
  myproc foo (42; named=1)
  '

  # extra block.  TODO: error is about typed args
  _error-case-X 3 '
  proc myproc (w; p; n) {
    echo hi
  }
  myproc foo (42; n=1) { echo hi }
  '
}


test-func-defaults() {
  _error-case-X 1 'func f(a=ZZ) { echo }'
  _error-case-X 1 'func f(a; named=YY) { echo }'

  _expr-error-case 'func f(a=[]) { echo }'
  _expr-error-case 'func f(; d={a:3}) { echo }'
}

test-func-missing() {
  _expr-error-case '
  func f(x, y) {
    echo "$x $y"
  }
  call f(1)
  '

  _expr-error-case '
  func f(x, y; z) {
    echo "$x $y"
  }
  call f(3, 4)
  '

}

test-func-extra() {
  _expr-error-case '
  func f() {
    echo "$x $y"
  }
  call f(42)  # extra pos
  '

  _expr-error-case '
  func f() {
    echo "$x $y"
  }
  call f(; x=32)  # extra named
  '
}

test-func-passing() {
  # rest can't have default -- parse error
  _error-case-X 2 '
  func f(...rest=3) {
    return (42)
  }
  '

  _expr-error-case '
  func f(a, b) {
    echo "$a -- $b"
  }
  = f()
  '

  _expr-error-case '
  func f(a, b) {
    echo "$a -- $b"
  }
  = f(...[1, 2])
  = f(...3)
  '

  # rest args and splat
  _should-run '
  func f(a, ...b) {
    echo $a - @b -
  }
  = f(1, 2, 3)

  var x = [4, 5, 6]
  = f(...x)
  '

  # Named splat
  _should-run '
  func f(p ; a, b) {
    echo "$p ; $a $b"
  }
  var kwargs = {a: 42, b: 43, c: 44}
  = f(99; ...kwargs)
  '
}

test-read-builtin() {
  # no typed args
  _error-case-X 2 'echo hi | read (&x)'
  _error-case-X 2 'echo hi | read --all x y'
  _error-case-X 2 'echo hi | read --line x y'
}

test-equality() {
  _expr-error-case '
  = ^[42] === ^[43]
  '

  _expr-error-case '
  = ^(echo hi) === ^(echo yo)
  '

  return

  # Hm it's kind of weird you can do this -- it's False
  _expr-error-case '
  = ^[42] === "hi"
  '
}

test-place() {
  _expr-error-case '
  var a = null
  var p = &a
  call p->setValue()  # 1 arg
  '

  _expr-error-case '
  var a = null
  var p = &a
  call p->setValue(3, 4)
  '

  _error-case '
  func f() {
    var s = "foo"
    return (&s)

  }
  var p = f()
  call p->setValue(3)
  '

}

test-json() {
  _expr-error-case 'json write'
  _expr-error-case 'json write (42, 43)'

  _error-case-X 2 'json read zz'
  _error-case-X 2 'json read yy zz'
  _error-case-X 3 'json read (&x, 43)'
}

test-error-builtin() {

  _error-case-X 2 'error '
  _error-case-X 2 'error --'

  # These are OK
  _error-case-X 10 'error -- oops'
  _error-case-X 10 'error oops'

  _error-case-X 99 'error oops (status=99)'
}

test-fat-arrow() {
  #_should-run '= "str" -> upper()'
  _should-run '= "str" => upper()'

  _expr-error-case '= "str" -> bad()'

  # We get 'Undefined variable' error because of the fallback, could make it better
  _error-case-X 1 '= "str" => bad()'

  _should-run '= ["3", "4"] => join("/")'

  # Good error message for method chaining
  _expr-error-case '= "badstring" => join("/")'


  # float has no ExactlyEqual
  _error-case-X 3 "= [1.0, 2.0] => indexOf(3.14)"

  # Invalid type
  _expr-error-case '
  var myint = 42
  = "badstring" => myint("/")
  '
}

test-method-type-errors() {
   _expr-error-case '= "hi" => search(42)'
   _expr-error-case '= "hi" => leftMatch(42)'
   _expr-error-case "var m = 'hi' => leftMatch(/'hi'/); = m => group(3.14)"
}

test-str-replace() {
   # Some ad hoc tests - spec tests cover this
   if false; then
     _should-run '= "hi" => replace("i", "b")'
     _should-run '= "hi" => replace(/[a-z]/, "b")'
     _should-run '= "hi" => replace(/[a-z]/, "b", count=1)'
     _should-run '= "foo42" => replace(/<capture d+>/, ^"hi $1")'
     _should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi $num")'
     _should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi ${num}")'
     _should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi $[num]")'
     # test out globals - is this desirable?
     _should-run '= "foo42" => replace(/<capture d+ as num>/, ^["hi $[num] $PATH"])'
     # -1 is replace all
     _should-run '= "foo" => replace("o", "x", count=-1)'
     _should-run '= "foo" => replace("o", "x", count=-2)'
   fi
   # Replace empty string?  Weird Python behavior
   _should-run '= "foo" => replace("", "-")'
   _should-run '= "foo" => replace("", "-", count=2)'

   # Use Expr with string
   _should-run '= "foo" => replace("o", ^"-")'
   # $0 is regular $0 here
   _should-run '= "foo" => replace("o", ^"-$0")'

   # Hm $0 isn't set?
   _should-run '= "foo" => replace(/[o]/, ^"-$0")'
   # Here $1 is set
   _should-run '= "foo" => replace(/<capture [o]>/, ^"-$1")'
   _should-run '= "foo" => replace(/<capture [o] as letter>/, ^"-$letter")'

   # Invalid arguments
   _expr-error-case '= "foo" => replace(42, "x")'
   _expr-error-case '= "foo" => replace("x", 42)'

   # Invalid evaluation
   _expr-error-case '= "foo" => replace("x", ^[42])'
}

soil-run() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-runtime-errors run-test-funcs
}

"$@"
