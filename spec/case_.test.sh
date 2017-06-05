#!/bin/bash
#
# Test the case statement

### Case statement
case a in
  a) echo A ;;
  *) echo star ;;
esac
# stdout: A

### Case statement with ;;&
# ;;& keeps testing conditions
# NOTE: ;& and ;;& are bash 4 only, no on Mac
case a in
  a) echo A ;;&
  *) echo star ;;&
  *) echo star2 ;;
esac
# status: 0
# stdout-json: "A\nstar\nstar2\n"
# N-I dash stdout-json: ""
# N-I dash status: 2

### Case statement with ;&
# ;& ignores the next condition.  Why would that be useful?
case a in
  a) echo A ;&
  XX) echo two ;&
  YY) echo three ;;
esac
# status: 0
# stdout-json: "A\ntwo\nthree\n"
# N-I dash stdout-json: ""
# N-I dash status: 2

### Case with empty condition
case $empty in
  ''|foo) echo match ;;
  *) echo no ;;
esac
# stdout: match

### Match a literal with a glob character
x='*.py'
case "$x" in
  '*.py') echo match ;;
esac
# stdout: match

### Match a literal with a glob character with a dynamic pattern
x='b.py'
pat='[ab].py'
case "$x" in
  $pat) echo match ;;
esac
# stdout: match

### Quoted literal in glob pattern
x='[ab].py'
pat='[ab].py'
case "$x" in
  "$pat") echo match ;;
esac
# stdout: match
