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

split-join-demo() {
  var parts = @(aaa BB c)
  echo 'Parts:' @parts
  echo

  echo 'join(parts):' $join(parts)
  echo

  echo '+ Another way of doing it, without creating another variable:'
  echo -sep '' @parts
  echo

  var j = join(parts, ":")
  #var a = split(j)
  #repr j a

  echo -sep '' "j => " $j
  echo -sep '' 'When IFS is the default, split(j) => '
  echo @split(j)
  echo

  setvar IFS = ":"
  echo 'When IFS is :, split(j) => '
  echo @split(j)
  echo

  unset IFS

  echo '+ Since there is no word splitting of unquoted $(ls), here is an idiom:'
  echo @split( $(ls ~ | grep b) )
}

types-demo() {
  echo 'TODO: bool, int, etc.'
}

"$@"
