#!/usr/bin/env bash
#
# Usage:
#   demo/04-unicode.sh <function name>
# 
# TODO: Test what happens if you read binary data into a $(command sub)
# - internal NUL
# - invalid utf-8 sequence
#
# It would be nice to move some of this into test/gold?  It depends on the
# locale.

set -o nounset
set -o pipefail
set -o errexit

# https://www.gnu.org/software/bash/manual/bash.html#Shell-Parameter-Expansion
#
# See doc/unicode.txt.

unicode-char() {
  python -c 'print u"[\u03bc]".encode("utf-8")'
}

# http://stackoverflow.com/questions/602912/how-do-you-echo-a-4-digit-unicode-character-in-bash
echo-char() {
  #echo -e "\xE2\x98\xA0"
  echo -e "\xE2\x98\xA0"

  #echo -e "\x03\xbc"

  # Woah bash has this!  Interesting.  Not documented in "help echo" though.
  echo -e '\u2620'

  # GNU echo does not have it.
  /bin/echo -e '\u2620'
}

raw-char() {
  # Use vim to put utf-8 in this source file:
  # 1. i to enter Insert mode
  # 2. Ctrl-V
  # 3. u 
  # 4. 03bc  -- 4 digits of hex0
  echo [μ]
}

quoted-chars() {
  echo '[μ]'
  echo "[μ]"
  echo $'[\u03bc]'  # C-escaped string

  # Not implementing this
  # https://www.gnu.org/software/bash/manual/html_node/Locale-Translation.html
  echo $"hello"
}

test-unicode() {
  locale  # displays state
  echo
  echo $LANG

  unicode-char

  local u=$(unicode-char)
  echo $u

  # This changes bash behavior!

  #LANG=C
  echo ${#u}  # three chars

  # OK bash respect utf-8 when doing string slicing.  Does it have its own
  # unicode support, or does it use libc?
  echo ${u:0} ${u:1} ${u:2}

  local u=$(raw-char)
  echo ${u:0} ${u:1} ${u:2}
}

json() {
  python -c 'print "\"\u03bc\""' | python -c '
import sys, json
print json.loads(sys.stdin.read())
'

  # \0u000 code point seems to be representable
  python -c 'print "\"[\u0000]\""' | python -c '
import sys, json
print repr(json.loads(sys.stdin.read()))
'
  # Works in python3 too.
  python -c 'print "\"[\u0000]\""' | python3 -c '
import sys, json
print(repr(json.loads(sys.stdin.read())))
'
}

# Right now it's split into (Lit_Other '\xce') and (Lit_Other '\xbc').  This is
# fine for most purposes, although we could probably simplify this.
osh-literal() {
  bin/osh -n -c 'echo [μ]'
  # This works fine
  bin/osh -c 'echo [μ]'
}

# TODO
# - ltrace of bash, python, osh, ysh
# - LANG vs LC_ALL - LANG is the default
# - C or UTF-8 is accepted

libc-vars() {
  local sh=${1:-bin/osh}  # also _bin/cxx-asan/osh

  case $sh in
    _bin/*/osh)
      ninja $sh
      ;;
  esac

  $sh -c 'echo hi'
  echo

  LC_ALL=C $sh -c 'echo hi'
  echo

  LANG=C $sh -c 'echo hi'
  echo

  LC_COLLATE=C $sh -c 'echo hi'
  echo

  # this turns it into "C"
  LC_ALL=POSIX $sh -c 'echo hi'
  echo

  LC_ALL=zz $sh -c 'echo hi'
  echo

  # TODO: non-utf8
}

# Copied into spec/unicode.test.sh; mksh behaves differently
length-op() {
  for s in $'\u03bc' $'\U00010000'; do
    LC_ALL=
    echo "len=${#s}"

    LC_ALL=C
    echo "len=${#s}"
  done
}

compare-shells() {
  # hm they all support unicode
  for sh in bash zsh mksh; do
    echo "=== $sh"
    $sh $0 length-op
    echo
  done
}

len-1() {
  s=$'\U00010000'
  echo ${#s}
}

len-2() {
  s=$'\U00010000'
  s2=$'\u03bc'  # different string, so length isn't cached

  #s3=$'\uffff'  # different string, so length isn't cached
  #s2=$'\U0001000f'  # different string, so length isn't cached

  #echo ${#s} ${#s2}
  # I see more of these
  #  __ctype_get_mb_cur_max()     = 6
  # mbrtowc(0, 0xHEX, 3, 0xHEX)   = 2

  echo ${#s} ${#s2}
}

norm-ltrace() {
  grep mb $1 | sed --regexp-extended 's/0x[0-9a-f]+/0xHEX/g'
}

ltrace-diff() {
  ### Shows that bash calls decoding mbrtowc() when calculating string length!

  ltrace bash $0 len-1 2>_tmp/1.txt
  ltrace bash $0 len-2 2>_tmp/2.txt

  wc -l _tmp/{1,2}.txt

  diff -u <(norm-ltrace _tmp/1.txt) <(norm-ltrace _tmp/2.txt )
}
 

"$@"
