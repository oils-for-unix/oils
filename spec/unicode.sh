#!/usr/bin/env bash
#
# Usage:
#   ./unicode.sh <function name>
# 
# TODO: Test what happens if you read binary data into a $(command sub)
# - internal NUL
# - invalid utf-8 sequence

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

"$@"
