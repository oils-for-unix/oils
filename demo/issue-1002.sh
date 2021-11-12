#!/usr/bin/env bash

# This causes an segfault in bash and dash!  I think it's an infinite loop.
# zsh hangs
# trap term TERM

term() {
  kill 0  # terminates the current process group
}

main() {
  {
    #sleep 10
    while true; do
      echo '...'
      sleep 0.2
    done 
  } &

  echo 1
  echo foo | grep foo
  sleep 0.2

  echo 2
  echo bar | grep bar
  sleep 0.2

  echo 3
  echo baz | grep baz
  sleep 0.2

  term
}

main
