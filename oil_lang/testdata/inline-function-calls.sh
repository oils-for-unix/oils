#!/bin/bash
#
# Usage:
#   ./inline-function-calls.sh <function name>

shopt -s oil:basic

simple-demo() {
  var myarray = @(spam eggs ham)

  echo '+ Call in expression context:'
  var length = len(myarray)
  echo $length
  echo

  echo '+ Inline call that coerces to string:'
  write -- $len(myarray) $len("abc") ''
  echo

  echo '+ Inline calls can be part of a word:'
  write -- --length=$len(myarray) $len("abc")$len("xyz")
  echo

  echo "+ Caveat: can't double quote.  It would break programs."
  echo "  Should we add an option 'shopt -s parse_dparen'?"
  echo

  # NOTE: Oil's echo builtin takes --, and requires it here
  write -- "--length=$len(myarray)"
  echo

  echo '+ Just as you can splice @myarray'
  write -- @myarray
  echo

  echo '+ You can also splice the result of a function returning a sequence:'
  echo '  Notes:'
  echo '  - the sorted() function is from Python.'
  echo '  - sorting utf-8 encoded strings as bytes is well-defined'
  echo
  write -- @sorted(myarray)
  echo

  # But this is a syntax error
  #echo @sorted(myarray)@invalid
}

split-join-demo() {
  var parts = @(aaa BB c)
  write -- 'Parts:' @parts
  echo

  write 'join(parts):' $join(parts)
  echo

  echo '+ Another way of doing it, without creating another variable:'
  write -sep '' -- @parts
  echo

  var j = join(parts, ":")
  #var a = split(j)
  #repr j a

  write -sep '' "j => " $j
  write -sep '' 'When IFS is the default, split(j) => '
  write @split(j)
  echo

  setvar IFS = ":"
  echo 'When IFS is :, split(j) => '
  write @split(j)
  echo

  unset IFS

  echo '+ Since there is no word splitting of unquoted $(ls), here is an idiom:'
  write @split( $(ls ~ | grep b) )
}

types-demo() {
  echo 'TODO: bool, int, etc.'
}

all() {
  simple-demo
  split-join-demo
}

"$@"
