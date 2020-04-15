#!/bin/bash
#
# Prep for the "Ultimate Guide to errexit".
#
# Usage:
#   ./errexit-pitfalls.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

die() {
  echo "$@" >&2
  exit 1
}

#
# inherit_errexit (bash and Oil)
#
# It's confusing that command subs clear the errexit flag (but subshells
# don't.)

# This is a bash quirk
command-sub-needs-inherit-errexit() {
  echo $(echo 1; false; echo 2)

  echo 'inherit_errexit'
  shopt -s inherit_errexit || die "bash 4.4 required"

  echo $(echo 1; false; echo 2)
}

subshell-demo() {
  ( echo 1; false; echo 2 )  # prints 1
}

#
# more_errexit (Oil)
#
# It's confusing that a=$(false) is different than local a=$(false).

assignment-builtin-overwrites-status() {
  set +o errexit

  a=$(false)
  echo $?  # this is 1

  local b=$(false)
  echo $?  # surprisingly, it's 0!
}

oil-more-errexit() {
  shopt -s more_errexit

  local b=$(false)  # FAILS!
  echo $? 
}

#
# strict_errexit (Oil)
#
# It's confusing that 'if myfunc', 'while/until myfunc', 'myfunc || die',
# 'myfunc && echo OK' and '!  myfunc' change errexit.

myfunc() {
  echo '--- myfunc'
  ls /zz   # should cause failure
  echo "shouldn't get here"
}

proper-function-failure() {
  # Proper failure
  myfunc
  echo "Doesn't get here"
}

# Function calls in condition cause the function to IGNORE FAILURES
function-call-in-condition() {
  # All 4 of these surprisingly don't fail

  if myfunc; then
    echo 'if'
  fi

  myfunc && echo '&&'

  myfunc || echo 'not printed'

  ! myfunc
}

proper-lastpipe-failure() {
  { echo hi; exit 5; } | sort
  echo "doesn't get here"
}

# Same problem for pipelines, another compound command.
pipeline-in-conditionals() {
  # If the above function aborts early, then this one should too.
  if { echo hi; exit 5; } | sort; then
    echo true
  else
    echo false
  fi
  echo bad
}

#
# Conditional As Last Statement in Function Pitfall
#
# It's confusing that calling a one-line function with 'foo && echo OK' isn't
# the same as inlining that statement (due to differing exit codes).


# Possible strict_errexit rule:
#   Disallow && (an AndOr with && as one of the operators) unless it's in an
#   if/while/until condition.
# This would require an extra flag for _Execute().
#   cmd_flags | ERREXIT      (to avoid the stack)
#   cmd_flags | IS_CONDITION

last-func() {
  test -d nosuchdir && echo no dir
  echo survived

  set -e
  f() { test -d nosuchdir && echo no dir; }
  echo 'in function'
  f

  # We do NOT get here.
  echo survived
}


#
# Builtins
#

read-exit-status() {
  set +o errexit

  echo line > _tmp/line
  read x < _tmp/line  # status 0 as expected
  echo status=$?

  echo -n no-newline > _tmp/no
  read x < _tmp/no  # somewhat surprising status 1, because no delimiter read
  # This is for terminating loops?

  echo status=$?

  # Solution: Oil can have its own builtin.  It already has 'getline'.
  # getfile / slurp / readall
  # readall :x < myfile
  #
  # grep foo *.c | readall :results
  #
  # grep foo *.c | slurp :results  # I Kind of like this
  # 
  # Unlike $(echo hi), it includes the newline
  # Unlike read x, it doesn't fail if there's NO newline.
}


#
# lastpipe and SIGPIPE
#

# This is a bit of trivia about the exit status.
sigpipe-error() {
  set +o errexit
  busybox | head -n 1
  echo status=$?  # 141 because of sigpipe

  # Workaround
  { busybox || true; } | head -n 1
  echo status=$?
}

# 
# Other constructs I don't care about from https://mywiki.wooledge.org/BashFAQ/105
#

#
# - let i++
# - (( i++ ))

"$@"
