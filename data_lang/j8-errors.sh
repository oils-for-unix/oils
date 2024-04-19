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

test-parse-errors() {
  #echo OSH=$OSH
  #set +o errexit

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

test-lex-errors() {
  # ASCII control chars outside are disallowed
  _ysh-error-here-X 1 << 'EOF'
echo $'\x02' | json read
EOF

  # Unclosed quote
  _error-case-X 1 'echo [\" | json read'

  # EOL in middle of string
  _error-case-X 1 'echo -n [\" | json read'

   # Invalid string escape
  _ysh-error-here-X 1 << 'EOF'
echo '"hi \z bye"' | json read
EOF


  # Invalid unicode in string
  _ysh-error-here-X 1 << 'EOF'
# part of mu = \u03bc
echo $' "\xce" ' | json read
EOF

  #return

  # Invalid ASCII control chars inside string
  _ysh-error-here-X 1 << 'EOF'
echo $'"foo \x01 "' | json read
pp line (_reply)
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
