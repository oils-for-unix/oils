#!/usr/bin/env bash
#
# Usage:
#   demo/xtrace1.sh <function name>

#set -o nounset
#set -o pipefail
#set -o errexit

# Problem:
# - There is no indentation for function calls
# - There is no indication of the function call.  It only traces simple
# commands.  'local' is also traced with the concrete value.

myfunc() {
  local arg=$1
  echo "{ myfunc $arg"
  echo "myfunc $arg }"
}

main() {
  set -o xtrace

  echo '{ main'
  myfunc main
  echo 'main }'

  # No indentation or increase in +
  ( myfunc subshell)

  # Now we change to ++
  foo=$(myfunc commandsub)
  echo $foo

  # Still +
  myfunc pipeline | wc -l

  # Increase to three
  foo=$(echo $(myfunc commandsub))
  echo $foo

  # Call it recursively
  $0 myfunc dollar-zero

  # Call it recursively with 
  export SHELLOPTS
  $0 myfunc dollar-zero-shellopts

  echo
  echo
  echo

  # OK this is useful.

  # https://unix.stackexchange.com/questions/355965/how-to-check-which-line-of-a-bash-script-is-being-executed
  PS4='+${LINENO}: '

  # Test runtime errors like this
  #PS4='+${LINENO}: $(( 1 / 0 ))'

  myfunc ps4
  foo=$(myfunc ps4-commandsub)
  echo foo
}

my_ps4() {
  for i in {1..3}; do
    echo -n $i
  done
}

# The problem with this is you don't want to fork the shell for every line!

call_func_in_ps4() {
  set -x
  PS4='[$(my-ps4)] '
  echo one
  echo two
}

# EXPANDED argv is displayed, NOT the raw input.
# - OK just do assignments?

# - bash shows the 'for x in 1 2 3' all on one line
# - dash doesn't show the 'for'
# - neither does zsh and mksh
#   - zsh shows line numbers and the function name!

# - two statements on one line are broken up

# - bash doesn't show 'while'

# The $((i+1)) is evaluated.  Hm.

# Hm we don't implement this, only works at top level
# set -v

loop() {
  set -x

  for x in 1 \
    2 \
    3; do
    echo $x; echo =$(echo {x}-)
  done

  i=0
  while test $i -lt 3; do
    echo $x; echo ${x}-
    i=$((i+1))
    if true; then continue; fi
  done
}

atoms1() {
  set -x

  foo=bar

  # this messes up a lot of printing.  OSH will use QSN.
  x='one
  two'

  i=1

  [[ -n $x ]]; echo "$x"

  # $i gets expanded, not i
  (( y = 42 + i + $i )); echo yo

  [[ -n $x
  ]]

  (( y =
     42 +
     i +
     $i
  ))
}

atoms2() {
  set -x

  x='one
  two'

  declare -a a
  a[1]="$x"

  # This works
  declare -A A
  A["$x"]=1

  a=(1 2 3)
  A=([k]=v)

  a=("$x" $x)
  A=([k]="$x")

  # Assignment builtins

  declare -g -r d=0 foo=bar
  typeset t=1
  local lo=2
  export e=3 f=foo
  readonly r=4
}

compound() {
  set -x

  # Nothing for time
  time sleep 0

  # There is no tracing for () and {}
  { echo b1
    echo b2
  }

  ( echo c1
    echo c2
  )

  # no tracing for if; just the conditions
  if test -d /; then
    echo yes
  else
    echo no
  fi

  # Hm this causes a concurrency problem.
  # I think we want to buffer the line
  ls | wc -l | sort

  # There IS tracing for 'case' line
  case foo in
    fo*)
      echo case
      ;;
    *)
      echo default
      ;;
  esac

  f() {
    echo hi
  }

}

oil_constructs() {
  echo TODO
  # BareDecl, VarDecl, PlaceMutation, Expr
}

"$@"
