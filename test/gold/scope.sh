#!/usr/bin/env bash
#
# Demo of variable scope.

#set -o nounset
set -o pipefail
set -o errexit

printenv() {
  spec/bin/printenv.py "$@"
}

my_global=G1

myfunc() {
  # This makes a NEW local variable my_global.
  # Yeah I think this is amenable to static analysis.
  local loc1=L1 my_global loc2=L2

  my_global=LL
  echo "my_global in function: $my_global"

  loc1=L3
  echo "loc1: $loc1 loc2: $loc2"

  # TODO: Add declare
}

func2() {
  my_global=G2
  func2_global=G3

  local func2_local=A

  inner_func() {
    echo "called inner_func"
    #set -o nounset
    # Not defined anymore
    echo "func2_local: $func2_local"
  }
}

# Doesn't work until func2 is run
inner_func || echo "inner_func not defined yet"

myfunc
echo "my_global: $my_global"

func2

# This is defined outside
inner_func

echo "AFTER mutation my_global: $my_global"
echo "func2_global $func2_global"

# These don't leak
echo "loc1: $loc1 loc2: $loc2"

# Nothing can be combined.  Only one keyword.  Use declare flags to combine.
combined() {
  local __LOCAL=1
  export __ONE=one
  export local __TWO=two
  export readonly __THREE=three

  # does not work!
  local export __FOUR=four
  # does not work!
  readonly export __FIVE=five

  readonly local __SIX=six
  echo $SIX

  local readonly __SEVEN=seven
  echo $SEVEN
  #echo "readonly: [$readonly]"

  # This doesn't work!
  export readonly local __EIGHT=eight

  printenv __ONE __TWO __THREE __FOUR __FIVE __SIX __SEVEN __EIGHT
  # export can come first, but local can't come first

  # These are both -a
  local __array=(1 2 3)
  local __array2=([a]=1 [b]=2 [c]=3)

  # This gets -A
  local -A __array3=([a]=1 [b]=2 [c]=3)

  # Doesn't get any flags.  global/local is NOT a flag!  It's about the
  # position in the symbol tables I guess.
  declare -g __global=g

  declare -p | grep __
}

__GLOBAL=foo

combined
echo GLOBAL
declare -p | grep __

conditional-local() {
  if test $# -eq 0; then
    echo DEFINING LOCAL
    local x=1
    echo $x
  else
    echo DEFINING GLOBAL
    x=2
    echo $x
  fi

  x=3
  echo $x
}

conditional-local
echo $x  # x is not defined

conditional-local foo
echo $x  # x is not defined


