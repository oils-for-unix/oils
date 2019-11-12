#!/usr/bin/env bash
#
# Test the case statement

#### Case statement
case a in
  a) echo A ;;
  *) echo star ;;
esac
## stdout: A

#### Case statement with ;;&
# ;;& keeps testing conditions
# NOTE: ;& and ;;& are bash 4 only, no on Mac
case a in
  a) echo A ;;&
  *) echo star ;;&
  *) echo star2 ;;
esac
## status: 0
## stdout-json: "A\nstar\nstar2\n"
## N-I dash stdout-json: ""
## N-I dash status: 2

#### Case statement with ;&
# ;& ignores the next condition.  Why would that be useful?
case a in
  a) echo A ;&
  XX) echo two ;&
  YY) echo three ;;
esac
## status: 0
## stdout-json: "A\ntwo\nthree\n"
## N-I dash stdout-json: ""
## N-I dash status: 2

#### Case with empty condition
case $empty in
  ''|foo) echo match ;;
  *) echo no ;;
esac
## stdout: match

#### Match a literal with a glob character
x='*.py'
case "$x" in
  '*.py') echo match ;;
esac
## stdout: match

#### Match a literal with a glob character with a dynamic pattern
x='b.py'
pat='[ab].py'
case "$x" in
  $pat) echo match ;;
esac
## stdout: match

#### Quoted literal in glob pattern
x='[ab].py'
pat='[ab].py'
case "$x" in
  "$pat") echo match ;;
esac
## stdout: match

#### Multiple Patterns Match
x=foo
result='-'
case "$x" in
  f*|*o) result="$result X"
esac
echo $result
## stdout: - X

#### Match one unicode char

# These two code points form a single character.
two_code_points="__$(echo $'\u0061\u0300')__"

# U+0061 is A, and U+0300 is an accent.  
#
# (Example taken from # https://blog.golang.org/strings)
#
# However ? in bash/zsh only counts CODE POINTS.  They do NOT take into account
# this case.

for s in '__a__' '__μ__' "$two_code_points"; do
  case $s in
    __?__)
      echo yes
      ;;
    *)
      echo no
  esac
done
## STDOUT:
yes
yes
no
## END
## BUG dash/mksh STDOUT:
yes
no
no
## END

#### case with single byte LC_ALL=C

LC_ALL=C

c=$(printf \\377)

# OSH prints -1 here
#echo "${#c}"

case $c in
  '')   echo a ;;
  "$c") echo b ;;
esac

## STDOUT:
b
## END
