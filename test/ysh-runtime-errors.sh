#!/usr/bin/env bash
#
# Usage:
#   test/ysh-runtime-errors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source test/sh-assert.sh  # _assert-sh-status

#
# Cases
#

test-no-typed-args() {
  # Hm these could both be J8 notation
  #_ysh-error-1 'echo (42)'
  #_ysh-error-1 'write (42)'

  _ysh-error-X 2 'true (42)'
  _ysh-error-X 2 'false { echo hi }'
}

test-undefined-vars() {
  _ysh-error-1 'echo hi; const y = 2 + x + 3'
  _ysh-error-1 'if (x) { echo hello }'
  _ysh-error-1 'if (${x}) { echo hi }'

  # BareDecl and regex
  _ysh-error-1 'const x = / @undef /; echo hi'

  _ysh-error-1 'var x = undef; echo $x'  # VarDecl
  _ysh-error-1 'setvar a = undef'  # PlaceMutation
}

test-word-eval-with-ysh-data() {
  _ysh-expr-error 'var d = {}; echo ${d:-}'

  _osh-error-X 3 'var d = {}; echo ${#d}'

  _osh-error-X 3 'var d = {}; echo ${d[0]}'

  _osh-error-X 3 'var d = {}; echo ${d[@]:1:3}'

  _osh-error-X 3 'var d = {}; echo ${!d}'

  _osh-error-X 3 'var d = {}; echo ${!d[@]}'

  _osh-error-X 3 'var d = {}; echo ${d#prefix}'

  _osh-error-X 3 'var d = {}; echo ${d//a/b}'

}

test-ysh-word-eval() {
  # Wrong sigil
  _ysh-expr-error 'echo $[maybe("foo")]'

  # Wrong sigil
  _ysh-expr-error 'source --builtin funcs.ysh; echo $[identity({key: "val"})]'

  # this should be consistent
  _ysh-expr-error 'source --builtin funcs.ysh; write -- @[identity([{key: "val"}])]'

  _ysh-expr-error 'const x = [1, 2]; echo $x'

  _ysh-should-run 'var x = [1, 2]; write @x'

  # errors in items
  _ysh-expr-error 'var x = [3, {}]; write @x'

  _ysh-expr-error 'var x = [3, {}]; write @[x]'

  # errors at top level
  _ysh-expr-error 'var x = /d+/; write @x'

  _ysh-expr-error 'var x = /d+/; write @[x]'
}

test-ysh-expr-eval() {
  _ysh-expr-error 'echo $[42 / 0 ]'

  _ysh-expr-error 'var d = {}; var item = d->nonexistent'

  _ysh-expr-error 'var d = {}; var item = d["nonexistent"]'

  _ysh-expr-error 'var a = []; setvar item = a[1]'

  _ysh-expr-error 'const x = 42 / 0'

  # command sub as part of expression retains its exit code
  _ysh-error-1 'var x = "z" ++ $(false)'
  #_ysh-error-1 'var x = "z" ++ $(exit 42)'

  _ysh-expr-error 'case (42 / 0) { * { echo hi } }; echo OK'

  _ysh-expr-error 'var d = {}; for x in $[d->zzz] { echo hi }'

  # Wrong index type
  _ysh-expr-error 'var d = {}; setvar d[42] = 3'
  _ysh-expr-error 'var L = []; setvar L["key"] = 3'

}

test-ysh-expr-eval-2() {
  _ysh-expr-error 'var L = []; var slice = L["foo": "bar"]'

  _ysh-expr-error '= 3 < true'
  _ysh-expr-error '= "a" < "b"'

  _ysh-expr-error 'var key = 42; var d = {[key]: 3}'

  _ysh-expr-error 'var d = {}; var a = d.a'
  _ysh-expr-error 'var d = []; var a = d.a'

  _ysh-expr-error '= 3 ** -2'
  _ysh-expr-error '= 3.2 ** 2'

  _ysh-expr-error '= - "foo"'
}

test-user-reported() {
  #_ysh-error-1 'echo'

  # Issue #1118
  # Some tests became test/parse-errors.sh


  # len(INTEGER) causes the same problem
  _ysh-expr-error '
  var snippets = [{status: 42}]
  for snippet in (snippets) {
    if (len(42)) {
      echo hi
    }
  }
  '

  # len(INTEGER) causes the same problem
  _ysh-expr-error '
  var count = 0

  # The $ causes a weird error
  while (count < len(count)) {
    setvar count += 1
  }
  '
}

test-fallback-locations() {
  # Melvin noticed bug here
  _ysh-expr-error 'if (len(42)) { echo hi }'

  # Be even more specific
  _ysh-expr-error 'if (1 + len(42)) { echo hi }'

  # From Aidan's PR -- redefinition
  _ysh-error-1 'const f = 42; func f() { echo hi }'

  # ForEach shell
  _ysh-expr-error 'for x in $[2 + len(42)] { echo hi }'

  # ForEach YSH
  _ysh-expr-error 'for x in (len(42)) { echo hi }'

  _ysh-expr-error 'while (len(42)) { echo hi }'

  _ysh-expr-error 'case (len(42)) { pat { echo argument } }'
  _ysh-expr-error 'case (42) { (len(42)) { echo arm } }'

  _ysh-expr-error 'case "$[len(42)]" in pat) echo hi ;; esac'

  _ysh-expr-error 'var x = 3 + len(42)'
  _ysh-expr-error 'const x = 3 + len(42)'
  _ysh-expr-error 'setvar x = 3 + len(42)'

  _ysh-expr-error 'setvar x = "s" + 5'
  _ysh-expr-error 'while ("s" + 5) { echo yes } '

  #_ysh-expr-error 'func f(x) { return (x) }; var x = f([1,2])(3); echo $x'

  # Really bad one
  _ysh-expr-error 'func f(x) { return (x) }; var x = f([1,2])[1](3); echo $x'
}

test-EvalExpr-calls() {
  ### Test everywhere expr_ev.EvalExpr() is invoked

  _ysh-expr-error 'json write (len(42))'

  _ysh-expr-error '= len(42)'
  _ysh-expr-error 'call len(42)'

  _ysh-expr-error 'echo $[len(42)]'
  _ysh-expr-error 'echo $[len(z = 42)]'

  _ysh-expr-error 'echo @[len(42)]'
  _ysh-expr-error 'echo @[len(z = 42)]'

  _ysh-expr-error 'const x = len(42)'
  _ysh-expr-error 'setvar x += len(42)'

  _ysh-expr-error '
    var d = {}
    setvar d[len(42)] = "foo"
  '

  _ysh-error-X 2 '
    var d = {}
    setvar len(42).z = "foo"
  '

  _ysh-expr-error '
  hay define Package
  Package foo {
    x = len(42)
  }
  '

  _ysh-expr-error 'if (len(42)) { echo hi }'

  _ysh-expr-error 'while (len(42)) { echo hi }'

  _ysh-expr-error 'for x in (len(42)) { echo $x }'
}


test-hay() {
  _ysh-error-X 127 '
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
  _osh-error-X 2 '
hay define package TASK

package foo {
  version = 1
}
'

   # forgot parse_equals
  _osh-error-X 127 '
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
  _ysh-should-run ' = / [ \x00 \xff ] /'
  _ysh-should-run ' = / [ \x00-\xff ] /'

  # Shouldn't be in strings

  cat >_tmp/test-eggex.txt <<'EOF'
= / [ $'\x00 \xff' ] /
EOF

  _ysh-error-1 "$(cat _tmp/test-eggex.txt)"

  _ysh-should-run ' = / [ \u{0} ] /'
  _ysh-should-run ' = / [ \u{0}-\u{1} ] /'

  # Too high
  _ysh-error-1 'var x =/ [ \u{80} ] /; echo $x'
  _ysh-error-1 'var x = / [ \u{7f}-\u{80} ] /; echo $x'

  # Now test special characters
  _ysh-should-run "$(cat <<'EOF'
= / [ \\ '^-]' 'abc' ] /
EOF
)"

  # Special chars in ranges are disallowed for simplicity
  _ysh-error-1 "var x = / [ a-'^' ] /; echo \$x"
  _ysh-error-1 "var x = / [ '-'-z ] /; echo \$x"
  _ysh-error-1 "var x = / [ ']'-z ] /; echo \$x"

  # TODO: Disallow this.  It translates to [^], which is a syntax error in
  # egrep "Unmatched [ or [^"
  _ysh-should-run "var x = / ['^'] /; echo \$x"

  _ysh-expr-error '
  var i = 42
  = / @i /   # splice object of wrong type
  '

  _ysh-expr-error '
  var i = 42
  = / [a @i] /   # char class splice object of wrong type
  '
}

test-eggex-2() {
  _ysh-should-run "var sq = / 'foo'+ /"

  _ysh-should-run "$(cat <<'EOF'
  var sq = / ('foo')+ /
  echo $sq

  var sq2 = / <capture 'foo'>+ /
  echo $sq2
EOF
)"

  _ysh-error-1 '
  var literal = "foo"
  var svs = / @literal+ /
  echo $svs
  '
}

test-eggex-api() {
  _ysh-expr-error '= _group(0)'  # No groups

  _ysh-expr-error 'if ("foo" ~ /[a-z]/) { echo $[_group(1)] }'
  _ysh-expr-error 'if ("foo" ~ /[a-z]/) { echo $[_group("name")] }'

  # ERE
  _ysh-expr-error 'if ("foo" ~ "[a-z]") { echo $[_group(1)] }'
  _ysh-expr-error 'if ("foo" ~ "[a-z]") { echo $[_group("name")] }'

  _ysh-expr-error '= _group("foo")'  # No such group
}

test-eggex-convert-func() {

  _ysh-should-run '= / <capture d+ as month: int> /'
  _ysh-should-run '= / <capture d+: int> /'
  _ysh-should-run '= / <capture d+> /'

  # bad convert func
  _ysh-expr-error '= / <capture d+ as month: BAD> /'
  _ysh-expr-error '= / <capture d+: BAD> /'

  # type error calling convert func (evalExpr)
  _ysh-expr-error 'var pat = / <capture d+: evalExpr> /; var m = "10" => search(pat) => group(1)'
}

test-int-convert() {
  _ysh-expr-error '= int({})'
  _ysh-expr-error '= int([])'
  _ysh-expr-error '= int("foo")'
  _ysh-expr-error '= int(len)'
  _ysh-expr-error '= int("foo"->startswith)'
}

test-float-convert() {
  _ysh-expr-error '= float({})'
  _ysh-expr-error '= float([])'
  _ysh-expr-error '= float("foo")'
  _ysh-expr-error '= float(len)'
  _ysh-expr-error '= float("foo"->startswith)'
}

test-str-convert() {
  _ysh-expr-error '= str({})'
  _ysh-expr-error '= str([])'
  _ysh-expr-error '= str(len)'
  _ysh-expr-error '= str("foo"->startswith)'
}

test-list-convert() {
  _ysh-expr-error '= list(1)'
  _ysh-expr-error '= list(len)'
  _ysh-expr-error '= list("foo"->startswith)'
}

test-dict-convert() {
  _ysh-expr-error '= dict(1)'
  _ysh-expr-error '= dict("foo")'
  _ysh-expr-error '= dict(len)'
  _ysh-expr-error '= dict("foo"->startswith)'
  _ysh-expr-error '= dict([["too", "many", "parts"]])'
}

test-proc-error-locs() {

  # positional
  _ysh-expr-error '
  var d = [1]

  func f(a=1, x=d[2]) {
    echo hi
  }
  '

  _ysh-expr-error '
  var d = [1]

  func f(; n=1, m=d[2]) {
    echo hi
  }
  '
}

test-func-error-locs() {
  # free funcs
  _ysh-expr-error '= join(["foo", "bar"], " ", 99)' # too many args
  _ysh-expr-error '= int()' # not enough args
  _ysh-expr-error '= str({})' # wrong type

  # bound funcs
  _ysh-expr-error '= "foo"->startswith("f", "o")' # too many args
  _ysh-expr-error '= "foo"->startswith()' # not enough args
  _ysh-expr-error '= "foo"->startswith(1)' # wrong type

  _ysh-expr-error '
  func f(x) {
     return (x)
  }
  = f()
  '
}

test-var-decl() {
  _ysh-expr-error 'var x, y = 1, 2, 3'
  _ysh-expr-error 'setvar x, y = 1, 2, 3'
}

test-const-decl() {
  _ysh-error-1 'const x = {}; const x = {};'
  _ysh-error-1 'const x; const x;'
}

test-proc-defaults() {
  
  # should be string
  _ysh-expr-error 'proc p(word=42) { echo }'
  _ysh-expr-error 'proc p(word=null) { echo }'

  # should be ^() or null
  _ysh-expr-error 'proc p( ; ; ; block="str") { echo }'
  _ysh-expr-error 'proc p( ; ; ; block=[]) { echo }'

  _ysh-should-run 'proc p( ; ; ; block=^(echo hi)) { true }'
  _ysh-should-run 'proc p( ; ; ; block=null) { true }'

  # divide by zero
  _ysh-expr-error 'proc p(word; t=42/0) { echo }'

  _ysh-error-X 1 'proc p(word; t=f()) { echo }'

  _ysh-error-X 1 'proc p(word; t=42; named=undef) { echo }'

  _ysh-error-X 1 'proc p(word; t=42; named=43; block=ZZ) { echo }'

  _ysh-should-run '
  proc p(word="yo"; t=42; named=43; block=null) {
    #echo $word $t $named $block
    echo $word $t $block
  }
  p
  '
}

test-proc-passing() {
  # Too few words
  _ysh-error-X 3 '
  proc p(a, b) { echo }
  p a
  '

  # Too many words
  _ysh-error-X 3 '
  proc p(a, b) { echo }
  p AA b c DD
  '

  # Too few typed
  _ysh-error-X 3 '
  proc p( ; a, b) { echo }
  p (42)
  '

  # Too many words
  _ysh-error-X 3 '
  proc p( ; a, b) { echo }
  p (42, 43, 44, 45)
  '

  _ysh-expr-error '
  proc p(; a, b) {
    echo $a - $b -
  }
  p (...[1, 2])
  p (...3)
  '

  # positional: rest args and spread
  _ysh-should-run '
  proc p(; a, ...b) {
    echo $a - @b -
  }
  p (1, 2, 3)

  var x = [4, 5, 6]
  p (...x)
  '

  # named: splat
  _ysh-should-run '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  var kwargs = {a: 42, b: 43}
  myproc (99; ...kwargs)
  '

  # named: rest args
  _ysh-should-run '
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
  _ysh-error-X 3 '
  proc myproc (w) {
    = w
  }
  myproc
  '

  # missing typed param
  _ysh-error-X 3 '
  proc myproc (w; t1, t2) {
    = w
    = t
  }
  myproc foo (42)
  '

  # missing named param
  _ysh-error-X 3 '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  myproc (99, b=3)
  '

  # missing named param with semicolon
  _ysh-error-X 3 '
  proc myproc (; p ; a, b) {
    echo "$p ; $a $b"
  }
  myproc (99; b=3)
  '

  # missing block param
  _ysh-error-X 3 '
  proc myproc (w; p ; a, b; block) {
    = block
  }
  myproc foo (99, a=1, b=2)
  '
}

test-proc-extra() {

  # extra word
  _ysh-error-X 3 '
  proc myproc () {
    echo hi
  }
  myproc foo
  '

  # extra positional
  _ysh-error-X 3 '
  proc myproc (w) {
    echo hi
  }
  myproc foo (42)
  '

  # extra named
  _ysh-error-X 3 '
  proc myproc (w; p) {
    echo hi
  }
  myproc foo (42; named=1)
  '

  # extra block.  TODO: error is about typed args
  _ysh-error-X 3 '
  proc myproc (w; p; n) {
    echo hi
  }
  myproc foo (42; n=1) { echo hi }
  '
}


test-func-defaults() {
  _ysh-error-X 1 'func f(a=ZZ) { echo }'
  _ysh-error-X 1 'func f(a; named=YY) { echo }'

  _ysh-expr-error 'func f(a=[]) { echo }'
  _ysh-expr-error 'func f(; d={a:3}) { echo }'
}

test-func-missing() {
  _ysh-expr-error '
  func f(x, y) {
    echo "$x $y"
  }
  call f(1)
  '

  _ysh-expr-error '
  func f(x, y; z) {
    echo "$x $y"
  }
  call f(3, 4)
  '

}

test-func-extra() {
  _ysh-expr-error '
  func f() {
    echo "$x $y"
  }
  call f(42)  # extra pos
  '

  _ysh-expr-error '
  func f() {
    echo "$x $y"
  }
  call f(; x=32)  # extra named
  '
}

test-func-passing() {
  # rest can't have default -- parse error
  _ysh-error-X 2 '
  func f(...rest=3) {
    return (42)
  }
  '

  _ysh-expr-error '
  func f(a, b) {
    echo "$a -- $b"
  }
  = f()
  '

  _ysh-expr-error '
  func f(a, b) {
    echo "$a -- $b"
  }
  = f(...[1, 2])
  = f(...3)
  '

  # rest args and splat
  _ysh-should-run '
  func f(a, ...b) {
    echo $a - @b -
  }
  = f(1, 2, 3)

  var x = [4, 5, 6]
  = f(...x)
  '

  # Named splat
  _ysh-should-run '
  func f(p ; a, b) {
    echo "$p ; $a $b"
  }
  var kwargs = {a: 42, b: 43, c: 44}
  = f(99; ...kwargs)
  '
}

test-read-builtin() {
  # no typed args
  _ysh-error-X 2 'echo hi | read (&x)'
  _ysh-error-X 2 'echo hi | read --all x y'
  _ysh-error-X 2 'echo hi | read --line x y'
}

test-equality() {
  _ysh-expr-error '
  = ^[42] === ^[43]
  '

  _ysh-expr-error '
  = ^(echo hi) === ^(echo yo)
  '

  return

  # Hm it's kind of weird you can do this -- it's False
  _ysh-expr-error '
  = ^[42] === "hi"
  '
}

test-float-equality() {
  _ysh-expr-error '
var x = 1
pp line (42.0 === x)'

  _ysh-expr-error 'pp line (2.0 === 1.0)'
}

test-place() {
  _ysh-expr-error '
  var a = null
  var p = &a
  call p->setValue()  # 1 arg
  '

  _ysh-expr-error '
  var a = null
  var p = &a
  call p->setValue(3, 4)
  '

  _ysh-error-1 '
  func f() {
    var s = "foo"
    return (&s)

  }
  var p = f()
  call p->setValue(3)
  '

}

test-json() {
  _ysh-expr-error 'json write'
  _ysh-expr-error 'json write (42, 43)'

  _ysh-error-X 2 'json read zz'
  _ysh-error-X 2 'json read yy zz'
  _ysh-error-X 3 'json read (&x, 43)'
}

# For decoding errors, see data_lang/j8-errors.sh

test-error-builtin() {

  _ysh-error-X 2 'error '
  _ysh-error-X 2 'error --'

  # These are OK
  _ysh-error-X 10 'error -- oops'
  _ysh-error-X 10 'error oops'

  _ysh-error-X 99 'error oops (code=99)'
}

test-fat-arrow() {
  #_ysh-should-run '= "str" -> upper()'
  _ysh-should-run '= "str" => upper()'

  _ysh-expr-error '= "str" -> bad()'

  # We get 'Undefined variable' error because of the fallback, could make it better
  _ysh-error-X 1 '= "str" => bad()'

  _ysh-should-run '= ["3", "4"] => join("/")'

  # Good error message for method chaining
  _ysh-expr-error '= "badstring" => join("/")'


  # float has no ExactlyEqual
  _ysh-error-X 3 "= [1.0, 2.0] => indexOf(3.14)"

  # Invalid type
  _ysh-expr-error '
  var myint = 42
  = "badstring" => myint("/")
  '
}

test-method-type-errors() {
   _ysh-expr-error '= "hi" => search(42)'
   _ysh-expr-error '= "hi" => leftMatch(42)'
   _ysh-expr-error "var m = 'hi' => leftMatch(/'hi'/); = m => group(3.14)"
}

test-str-replace() {
   # Some ad hoc tests - spec tests cover this
   if false; then
     _ysh-should-run '= "hi" => replace("i", "b")'
     _ysh-should-run '= "hi" => replace(/[a-z]/, "b")'
     _ysh-should-run '= "hi" => replace(/[a-z]/, "b", count=1)'
     _ysh-should-run '= "foo42" => replace(/<capture d+>/, ^"hi $1")'
     _ysh-should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi $num")'
     _ysh-should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi ${num}")'
     _ysh-should-run '= "foo42" => replace(/<capture d+ as num>/, ^"hi $[num]")'
     # test out globals - is this desirable?
     _ysh-should-run '= "foo42" => replace(/<capture d+ as num>/, ^["hi $[num] $PATH"])'
     # -1 is replace all
     _ysh-should-run '= "foo" => replace("o", "x", count=-1)'
     _ysh-should-run '= "foo" => replace("o", "x", count=-2)'
   fi
   # Replace empty string?  Weird Python behavior
   _ysh-should-run '= "foo" => replace("", "-")'
   _ysh-should-run '= "foo" => replace("", "-", count=2)'

   # Use Expr with string
   _ysh-should-run '= "foo" => replace("o", ^"-")'
   # $0 is regular $0 here
   _ysh-should-run '= "foo" => replace("o", ^"-$0")'

   # Hm $0 isn't set?
   _ysh-should-run '= "foo" => replace(/[o]/, ^"-$0")'
   # Here $1 is set
   _ysh-should-run '= "foo" => replace(/<capture [o]>/, ^"-$1")'
   _ysh-should-run '= "foo" => replace(/<capture [o] as letter>/, ^"-$letter")'

   # Invalid arguments
   _ysh-expr-error '= "foo" => replace(42, "x")'
   _ysh-expr-error '= "foo" => replace("x", 42)'

   # Invalid evaluation
   _ysh-expr-error '= "foo" => replace("x", ^[42])'
}

test-remainder() {
  # second number can't be negative
  _ysh-expr-error '= 5 % -3'
  _ysh-expr-error 'var x = 5; setvar x %= -3'
}

test-append-usage-error() {
  _ysh-should-run 'append x ([])'

  _ysh-expr-error 'append'

  _ysh-expr-error 'append x'  # Too few

  _ysh-expr-error 'append x ([], [])'  # Too many
}

# Bad error location
test-try-usage-error() {
  _ysh-expr-error '
var s = "README"
case (s) {
  README { echo hi }
}
echo hi

try myproc
if (_status !== 0) {
  echo failed
}
'
}

test-trim-utf8-error() {
  _ysh-error-here-X 3 << 'EOF'
  var badUtf = b'\yF9'

  # error is missed
  call " a$[badUtf]b " => trim()
  echo status=$_status

  # error is found
  call "$[badUtf]b " => trim()
EOF
}

test-setglobal() {
   _ysh-should-run '
var a = [0]
setglobal a[1-1] = 42
pp line (a)
   '

   _ysh-expr-error '
var a = [0]
setglobal a[a.bad] = 42
pp line (a)
   '

   _ysh-should-run '
var d = {e:{f:0}}
setglobal d.e.f = 42
pp line (d)
setglobal d.e.f += 1
pp line (d)
   '
}

test-assert() {
  _ysh-expr-error 'assert [null === 42]'

  # One is long
  _ysh-expr-error 'assert [null === list(1 .. 100)]'

  # Both are long
  _ysh-expr-error '
assert [{k: list(3 .. 50)} === list(1 .. 100)]
  '
}

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  local ysh=_bin/cxx-asan/ysh
  ninja $ysh
  YSH=$ysh run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-runtime-errors run-test-funcs
}

"$@"
