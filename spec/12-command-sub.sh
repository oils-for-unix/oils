#!/usr/bin/env bash


sleep_test() {
  echo "Sleeping for 10 seconds in subshell of PID $$"
  type sleep  # external command

  # NOTE: Within a subshell, $$ returns the PID of the script, not the subshell!

  # process tree for dash and bash looks different.
  #
  # dash appears to run the first thing not in a subshell?  Hm maybe I could do
  # that too.  But then global var references would be different.

  ( echo "PID $$"; sleep 10 ) | tee foo.txt
  #( echo "PID $BASHPID"; sleep 10 )

  # This doesn't cause an extra subshell in bash.
  ( sleep 10 )
}

g=0

myfunc() {
  echo 'running myfunc'
  g=1
}

# Hm bash and dash both seem to behave the same here.
var_test() {
  myfunc | tee _tmp/command-sub.txt
  { g=2; echo brace; } | tee _tmp/command-sub.txt

  echo "g after pipeline: $g"
}

#sleep_test "$@"

var_test
