#!/bin/bash
#
# Usage:
#   ./inline-function-calls.sh <function name>

shopt -s all:oil

simple-demo() {
  var myarray = @(spam eggs ham)

  echo '+ Call in expression context:'
  var length = len(myarray)
  echo $length
  echo

  echo '+ Inline call that coerces to string:'
  echo $len(myarray) $len("abc") ''
  echo

  echo '+ Inline calls can be part of a word:'
  echo -- --length=$len(myarray) $len("abc")$len("xyz")
  echo

  echo "+ Caveat: can't double quote.  It would break programs."
  echo "  Should we add an option 'shopt -s parse_dparen'?"
  echo

  # NOTE: Oil's echo builtin takes --, and requires it here
  echo -- "--length=$len(myarray)"
  echo

  echo '+ Just as you can splice @myarray'
  echo @myarray
  echo

  echo '+ You can also splice the result of a function returning a sequence:'
  echo '  Notes:'
  echo '  - the sorted() function is from Python.'
  echo '  - sorting utf-8 encoded strings as bytes is well-defined'
  echo
  echo @sorted(myarray)
  echo

  # But this is a syntax error
  #echo @sorted(myarray)@invalid
}

types-demo() {
  echo 'TODO: bool'
}

"$@"
