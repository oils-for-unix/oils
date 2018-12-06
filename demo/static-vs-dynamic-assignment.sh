#!/bin/bash
#
# TODO: Make this a spec test.
#
# Usage:
#   ./static-vs-dynamic-assignment.sh <function name>

argv() {
  spec/bin/argv.py "$@"
}

demo() {
  # dash behaves differently here!
  local x='X X'
  local y=$x  # no word splitting!
  argv "$y"

  # dash behaves differently here!
  local x='X z=ZZ'
  local y=$x  # no word splitting!
  argv "$y"

  # So basically each word is at most one assignment.  That is easy to
  # implement dynamically.  And then we can unify export and local again.

  local s='a=AA b=BB c'
  local "$s"     # This is a SINGLE assignment to a
  argv "$a" "$b"
  local $s       # This is multiple assignments to a, b, and c
                 # zsh behaves differently!
  argv "$a" "$b"

  local d='a=$a'  # note the single quotes!  It is NOT evaluated.
  local $d
  argv "$d"
  local "$d"
  argv "$d"

  local -a array
  array=(1 2 3)  # mksh doesn't allow initialization on one line

  # Doh, this is parsed by bash and zsh too!  And mksh somewhat supports it.
  #
  # So how do we re-run the parser?  Or should we omit this for now?
  # Don't allow dynamic a[x] assigments?  But 3 shells all implement it.

  local e='array[1+1]=42'
  local "$e"     # This is a SINGLE assignment to a
  argv "${array[@]}"

  # Hm why is this a parse error in bash!!
  # zsh allows this!!!
  # So it dequotes them first?  This makes no sense honestly.
  #local s='x="1 2 3"'
  local s="x='1 2 3'"
  local $s
  argv "$x"

  local s='x=1 2 3'
  # This results in a parse error!
  local $s
  argv "$x"
}

# dash is wrong
dash_demo() {
  dash $0 demo
}

# zsh is most lenient
zsh_demo() {
  zsh $0 demo
}

# mksh behaves more like bash
mksh_demo() {
  mksh $0 demo
}

"$@"
