#!/usr/bin/env bash
#
# Usage:
#   test/oil-runtime-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh

OIL=${OIL:-bin/oil}

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
  $OIL -c "$@"

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
  $OIL -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
}

test-regex-literals() {
  set +o errexit

  _should-run "var sq = / 'foo'+ /"

  _error-case '
  var dq = / "foo"+ /
  echo $dq
  '

  _should-run '
  var dq = / ("foo")+ /
  echo $dq

  var dq2 = / <"foo">+ /
  echo $dq2
  '

  _error-case '
  var literal = "foo"
  var svs = / $literal+ /
  echo $svs
  '

  _error-case '
  var literal = "foo"
  var bvs = / ${literal}+ /
  echo $bvs
  '
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

test-oil-word-eval() {
  set +o errexit

  _expr-error-case 'echo $maybe("foo")'

  _expr-error-case 'echo $identity({key: "val"})'

  # this should be consistent
  _expr-error-case 'write -- @identity([{key: "val"}])'

  _expr-error-case 'const x = [1, 2]; echo $x'
}

test-oil-expr-eval() {
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

test-EvalExpr-calls() {
  ### Test everywhere expr_ev.EvalExpr() is invoked

  _expr-error-case 'json write (len(42))'

  _expr-error-case '= len(42)'
  _expr-error-case '_ len(42)'

  _expr-error-case 'echo $[len(42)]'

  _expr-error-case 'echo $len(42)'
  _expr-error-case 'echo $len(z = 42)'

  _expr-error-case 'echo @len(42)'
  _expr-error-case 'echo @len(z = 42)'

  _expr-error-case 'const x = len(42)'
  _expr-error-case 'setvar x += len(42)'

  _expr-error-case '
    var d = {}
    = d[len("foo"), len(42)]
  '

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
  _error-case ' = / [ \u{80} ] /'
  _error-case ' = / [ \u{7f}-\u{80} ] /'

  # Now test special characters
  _should-run ' = / [ \\ "^-]" "abc" ] /'

  # Special chars in ranges are disallowed for simplicity
  _error-case " = / [ a-'^' ] /"
  _error-case " = / [ '-'-z ] /"
  _error-case " = / [ ']'-z ] /"

  # Hm this runs but will cause a syntax error.  Could disallow it.
  # _should-run ' = / ["^"] /'
}

soil-run() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release oil-runtime-errors run-test-funcs
}

"$@"
