#!/usr/bin/env bash
#
# Usage:
#   test/ysh-runtime-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh

YSH=${YSH:-bin/ysh}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_osh-error-case-X() {
  local expected_status=$1
  shift

  banner "$@"
  echo
  $OSH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != $expected_status; then
    die "Expected status $expected_status, got $status"
  fi
}


_error-case-X() {
  local expected_status=$1
  shift

  banner "$@"
  echo
  $YSH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != $expected_status; then
    die "Expected status $expected_status, got $status"
  fi
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
  banner "$@"
  echo
  $YSH -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
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
  _expr-error-case 'echo $[identity({key: "val"})]'

  # this should be consistent
  _expr-error-case 'write -- @[identity([{key: "val"}])]'

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

  _expr-error-case '= 3 < 4.0'
  _expr-error-case '= 3 < true'
  _expr-error-case '= "a" < "b"'

  _expr-error-case 'var key = 42; var d = {[key]: 3}'

  _expr-error-case 'var d = {}; var a = d.a'
  _expr-error-case 'var d = []; var a = d.a'

  _expr-error-case '= 3 ** -2'
  _expr-error-case '= 3.2 ** 2'

  _expr-error-case '= - "foo"'
  _expr-error-case '= not "foo"'
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
  _expr-error-case '_ len(42)'

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
    setvar len(42)->z = "foo"
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
    oops
  }

  bad 2
}
'

  ### shell assignment
  _error-case-X 2 '
hay define package user TASK

hay eval :result {
  package foo {
    version=1
  }
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

  var sq2 = / <'foo'>+ /
  echo $sq2
EOF
)"

  _error-case '
  var literal = "foo"
  var svs = / @literal+ /
  echo $svs
  '
}

soil-run() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-runtime-errors run-test-funcs
}

"$@"
