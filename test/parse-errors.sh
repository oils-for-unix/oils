#!/bin/bash
#
# Usage:
#   ./parse-errors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# Run with SH=bash too
SH=${SH:-bin/osh}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_error-case() {
  banner "$@"
  echo
  $SH -c "$@"
}

# All in osh/word_parse.py
patsub() {
  set +o errexit

  _error-case 'echo ${x/}'  # pattern must not be empty

  _error-case 'echo ${x/%}'  # pattern must not be empty (only had modifier)
  _error-case 'echo ${x/%/}'  # pattern must not be empty (only had modifier)

  # These are a little odd
  _error-case 'echo ${x//}'
  _error-case 'echo ${x///}'

  _error-case 'echo ${x/foo}'
  _error-case 'echo ${x//foo}'
  _error-case 'echo ${x///foo}'

  # Newline in replacement pattern
  _error-case 'echo ${x//foo/replace
}'
  _error-case 'echo ${x//foo/replace$foo}'
}

# osh/word_parse.py
word-parse() {
  set +o errexit

  _error-case 'echo ${'

  # This parses like a slice, but that's OK.  Maybe talk about arithmetic
  # expression.  Maybe say where it started?
  _error-case '${foo:}'

  _error-case 'echo ${a[@Z'

  _error-case 'echo ${x.}'
  _error-case 'echo ${!x.}'

  # Slicing
  _error-case 'echo ${a:1;}'
  _error-case 'echo ${a:1:2;}'

  # I don't seem to be able to tickle errors here
  #_error-case 'echo ${a:-}'
  #_error-case 'echo ${a#}'

  _error-case 'echo ${#a.'

  # for (( ))
  _error-case 'for (( i = 0; i < 10; i++ ;'
  # Hm not sure about this
  _error-case 'for (( i = 0; i < 10; i++ /'

  _error-case 'echo @(extglob|foo'
}

array-literal() {
  set +o errexit

  # Array literal with invalid TokenWord.
  _error-case 'a=(1 & 2)'
  _error-case 'a= (1 2)'
  _error-case 'a=(1 2'
}

arith-context() {
  set +o errexit

  # $(( ))
  _error-case 'echo $(( 1 + 2 ;'
  _error-case 'echo $(( 1 + 2 );'
  _error-case 'echo $(( '
  _error-case 'echo $(( 1'

  # Non-standard arith sub $[1 + 2]
  _error-case 'echo $[ 1 + 2 ;'

  # What's going on here?   No location info?
  _error-case 'echo $[ 1 + 2 /'

  _error-case 'echo $[ 1 + 2 / 3'
  _error-case 'echo $['

  # (( ))
  _error-case '(( 1 + 2 /'
  _error-case '(( 1 + 2 )/'
  _error-case '(( 1'
  _error-case '(('
}

arith-expr() {
  set +o errexit

  # BUG: the token is off here
  _error-case '$(( 1 + + ))'

  # BUG: not a great error either
  _error-case '$(( 1 2 ))'

  # Triggered a crash!
  _error-case '$(( - ; ))'
}

bool-expr() {
  set +o errexit

  # Extra word
  _error-case '[[ a b ]]'
  _error-case '[[ a "a"$(echo hi)"b" ]]'

  # Wrong error message
  _error-case '[[ a == ]]'

  # Invalid regex
  _error-case '[[ $var =~ * ]]'

  # Unbalanced parens
  _error-case '[[ ( 1 == 2 - ]]'

  _error-case '[[ == ]]'
  _error-case '[[ ) ]]'
  _error-case '[[ ( ]]'

  _error-case '[[ ;;; ]]'
  _error-case '[['
}

# These don't have any location information.
test-builtin() {
  set +o errexit

  # Extra token
  _error-case '[ x -a y f ]'
  _error-case 'test x -a y f'

  # Missing closing ]
  _error-case '[ x '

  # Hm some of these errors are wonky.  Need positions.
  _error-case '[ x x ]'

  _error-case '[ x x x ]'

  # -o tests if an option is enabled.
  #_error-case '[ -o x ]'
}

quoted-strings() {
  set +o errexit

  _error-case '"unterminated double'

  _error-case "'unterminated single"

  _error-case '
  "unterminated double multiline
  line 1
  line 2'

  _error-case "
  'unterminated single multiline
  line 1
  line 2"
}

cmd-parse() {
  set +o errexit

  _error-case 'echo < <<'
  _error-case 'echo $( echo > >>  )'
}

simple-command() {
  set +o errexit

  _error-case 'PYTHONPATH=. FOO=(1 2) python'
  _error-case 'echo foo FOO=(1 2)'

  _error-case 'PYTHONPATH+=1 python'
}

cases-in-strings() {
  set +o errexit

  cmd-parse
  simple-command

  # Word
  word-parse
  array-literal
  patsub
  quoted-strings

  # Arith
  arith-context
  arith-expr

  bool-expr
  test-builtin
}

# Cases in their own file
cases-in-files() {
  set +o errexit  # Don't fail

  for t in test/parse-errors/*.sh; do
    banner $t
    $SH $t
  done
}

all() {
  cases-in-strings

  echo
  echo ----------------------
  echo

  cases-in-files

  # Always passes
  return 0
}

run-for-release() {
  run-other-suite-for-release parse-errors all
}

"$@"
