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

  # $(( ))
  _error-case 'echo $(( 1 + 2 ;'
  _error-case 'echo $(( 1 + 2 );'

  # (( ))
  _error-case '(( 1 + 2 /'
  _error-case '(( 1 + 2 )/'

  # for (( ))
  _error-case 'for (( i = 0; i < 10; i++ ;'
  # Hm not sure about this
  _error-case 'for (( i = 0; i < 10; i++ /'

  _error-case 'echo @(extglob|foo'

  # Array literal with invalid TokenWord.
  _error-case 'a=(1 & 2)'
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


cases-in-strings() {
  set +o errexit

  _error-case 'echo < <<'
  _error-case '${foo:}'
  _error-case '$(( 1 +  ))'
  _error-case 'echo $( echo > >>  )'
  _error-case 'echo ${'

  patsub
  word-parse

  quoted-strings
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
