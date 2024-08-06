#!/usr/bin/env bash
#
# Usage:
#   demo/xtrace1.sh <function name>

#set -o nounset
#set -o pipefail
#set -o errexit

myfunc() {
  : "myfunc $1"
}

banner() {
  echo
  echo "$@"
  echo
}

# bash is the only shell with the "first char repeated" behavior
first_char() {
  for sh in bash dash mksh zsh bin/osh; do
    echo
    echo $sh
    export PS4='$PWD '
    #export PS4='$ '
    $sh -x -c 'echo $(echo hi)-'
  done
}

# bash repeats the + for command sub, eval, source.  Other shells don't.
posix() {
  banner COMMANDSUB
  set -x
  foo=$(myfunc commandsub)
  set +x

  # Hm this gives you ++
  banner EVAL
  set -x
  eval myfunc evalarg
  set +x

  # Also gives you ++
  banner SOURCE
  set -x
  . spec/testdata/source-argv.sh 1 2
  set +x
}

# Various stacks:
# - proc call stack (similar: FUNCNAME)
# - process stack (similar: BASHPID)
# - interpreter stack (eval, source.  xtrace already respects this)
#   - and maybe Oil subinterpreters

# User level:
# - Color
# - Indentation
# - HTML
#
# What you really want PARSEABLE traces.  Which means each trace item is ONE
# LINE.  And emitted by a single write() call.
#
# Related debugging features of OSH:
#
# - pp cell_ (ASDL), pp proc (QTT)
# - osh -n (ASDL)
# - Oil expressions: = keyword (ASDL)

shopt -s expand_aliases
alias e=echo

simple() {
  e alias
  myfunc invoke
  ( myfunc subshell )
}

main() {
  banner ALIAS

  set -x
  e alias
  set +x

  banner FUNC

  set -x
  myfunc invoke
  set +x

  banner SUBSHELL
  # No increase in +
  # pid and SHLVL do NOT increase.  BASHPID increases.
  set -x
  : pid=$$ BASHPID=$BASHPID SHLVL=$SHLVL
  ( myfunc subshell; : pid=$$ BASHPID=$BASHPID SHLVL=$SHLVL )
  set +x

  # Now it changes to ++
  banner COMMANDSUB
  set -x
  foo=$(myfunc commandsub)
  set +x

  banner PIPELINE
  set -x
  myfunc pipeline | sort
  set +x

  banner THREE

  # Increase to three
  set -x
  foo=$(echo $(myfunc commandsub))
  echo $foo
  set +x

  # Hm this gives you ++
  banner EVAL
  set -x
  eval myfunc evalarg
  set +x

  # Also gives you ++
  banner SOURCE
  set -x
  source spec/testdata/source-argv.sh 1 2
  set +x

  banner RECURSIVE
  set -x
  $0 myfunc dollar-zero
  set +x

  # TODO: SHELLOPTS not set here?
  banner "SHELLOPTS=$SHELLOPTS"

  export SHELLOPTS
  set -x
  $0 myfunc dollar-zero-shellopts
  set +x
}

main2() {
  set -x

  # OK this is useful.

  # https://unix.stackexchange.com/questions/355965/how-to-check-which-line-of-a-bash-script-is-being-executed
  PS4='+${LINENO}: '

  # Test runtime errors like this
  #PS4='+${LINENO}: $(( 1 / 0 ))'

  myfunc ps4
  foo=$(myfunc ps4-commandsub)
  echo foo
}

slowfunc() {
  for i in "$@"; do
    sleep 0.$i
  done
}

concurrency() {
  set -x

  # PID prefix would be nice here
  slowfunc 1 3 | slowfunc 2 4 5 | slowfunc 6
}

task() {
  for i in "$@"; do
    echo $i
    sleep 0.$i
  done
}

through_xargs() {
  set -x
  export PS4='+ $$ '

  # This doesn't work because xargs invokes $0!  Not OSH.
  export OILS_HIJACK_SHEBANG=1

  # This makes us trace through xargs.
  #
  # problem: $0 invokes bash because of the shebang.
  # We can't use $SHELL $0.
  # - bash is the only shell that sets $SHELL.
  # - It's not the right value.  "If it is not set when the shell starts, bash
  #   assigns to it the full pathname of the current user's login shell."

  export SHELLOPTS
  seq 6 | xargs -n 2 -P 3 -- $0 task
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

  # This messes up a lot of printing.
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

details() {
  PS4='+ ${BASH_SOURCE[0]}:${FUNCNAME[0]}:${LINENO} '

  # X_pid can have a space after it, or call it ${X_tag}
  # Or should we could call the whole thing ? ${XTRACE_PREFIX} ?
  # Idea: $PS5 and $PS6 for push and pop?

  # Problem: remove the first char behavior?  Or only respect it in PS4.
  #
  # This string can be OIL_XTRACE_PREFIX='' or something.
  PS4=' ${X_indent}${X_punct}${X_tag}${BASH_SOURCE[0]}:${FUNCNAME[0]}:${LINENO} '


  set -x

  echo hi
  echo command=$(echo inner)
  eval 'echo eval'
}

"$@"
