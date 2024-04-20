#!/usr/bin/env bash
#
# Usage:
#   data_lang/j8-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh  # $OSH, $YSH
source test/sh-assert.sh  # banner, _assert-sh-status

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

test-line-numbers() {
  # J8 string
  _osh-error-here-X 1 << 'EOF'
echo '
{
  "a": 99,
  "foo\z": 42
}
' | json read
EOF

  # JSON
  _osh-error-here-X 1 << 'EOF'
echo '
{
  "foo": 42 oops
}
' | json read
EOF

  # J8 Lines
  _ysh-error-here-X 4 << 'EOF'
proc p {
  echo unquoted
  echo
  echo
  echo ' "hi" oops'  # line 4 error
}

write -- @(p)
EOF
}

test-parse-errors() {
  # Unexpected EOF
  _error-case-X 1 'echo "" | json read'

  # Unexpected token
  _error-case-X 1 'echo { | json read'

  # Invalid token
  _error-case-X 1 'echo + | json read'

  # NIL8 token, not JSON8 token
  _error-case-X 1 'echo "(" | json read'

  # Extra input after valid message
  _ysh-error-here-X 1 << 'EOF'
echo '{}[ ' | json read
EOF

}

test-ascii-control() {
  # Disallowed ASCII control chars OUTSIDE string
  _osh-error-here-X 1 << 'EOF'
echo $'\x02' | json read
EOF
  # JSON
  _ysh-error-here-X 1 << 'EOF'
echo $'"foo \x01 "' | json read
pp line (_reply)
EOF
  # J8
  _ysh-error-here-X 1 << 'EOF'
var invalid = b'\y01'
echo $["u'foo" ++ invalid ++ "'"] | json8 read
pp line (_reply)
EOF
}

test-str-unclosed-quote() {
  # JSON
  _osh-error-here-X 1 << 'EOF'
echo -n '["' | json read
EOF
  # J8
  _osh-error-here-X 1 << 'EOF'
echo -n "[b'" | json8 read
EOF
}

test-str-bad-escape() {
   # Invalid string escape JSON
  _ysh-error-here-X 1 << 'EOF'
echo '"hi \z bye"' | json read
EOF
  _ysh-error-here-X 1 << 'EOF'
var invalid = r'\z'
echo $["u'hi" ++ invalid ++ "bye'"] | json8 read
EOF
return
}

test-str-invalid-utf8() {
  # JSON
  _ysh-error-here-X 1 << 'EOF'
# part of mu = \u03bc
echo $' "\xce" ' | json read
EOF
  # J8
  _ysh-error-here-X 1 << 'EOF'
var invalid = b'\yce'
echo $["u'" ++ invalid ++ "'"] | json8 read
EOF
}

test-encode() {
  _error-case-X 1 'var d = {}; setvar d.k = d; json write (d)'

  _error-case-X 1 'var L = []; call L->append(L); json write (L)'

  # This should fail!
  # But not pp line (L)
  _error-case-X 1 'var L = []; call L->append(/d+/); j8 write (L)'
}

test-cpython() {
  # control char is error in Python
  echo $'"foo \x01 "' \
    | python3 -c 'import json, sys; json.loads(sys.stdin.read())' || true
  echo $' \x01' \
    | python3 -c 'import json, sys; json.loads(sys.stdin.read())' || true
}

test-j8-lines() {
  _ysh-should-run-here <<'EOF'
write @(echo ' "json\tstring"  '; echo; echo " b'j8' "; echo ' unquoted ';)
EOF
  #return

  # quotes that don't match - in expression mode
  _ysh-error-here-X 4 <<'EOF'
var lines = @(
  echo '"unbalanced'
)
pp line (lines)
EOF

  # error in word language
  _ysh-error-here-X 4 <<'EOF'
write @(echo '"unbalanced')
EOF

  # can't have two strings on a line
  _ysh-error-here-X 4 <<'EOF'
write @(echo '"json" "nope"')
EOF

  _ysh-error-here-X 4 <<'EOF'
write @(echo '"json" unquoted')
EOF

  # syntax error inside quotes
  _ysh-error-here-X 4 <<'EOF'
write @(echo '"hello \z"')
EOF

  # unquoted line must be valid UTF-8
  _ysh-error-here-X 4 <<'EOF'
write @(echo $'foo \xff-bar spam')
EOF

  # unquoted line can't have ASCII control chars
  _ysh-error-here-X 4 <<'EOF'
write @(echo $'foo \x01-bar spam')
EOF
}



#
# Entry points
#

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  local osh=_bin/cxx-asan/osh
  ninja $osh
  OSH=$osh run-test-funcs
}

run-for-release() {
  run-other-suite-for-release j8-errors run-test-funcs
}

"$@"
