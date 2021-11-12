#!/usr/bin/env bash

# This causes an segfault in bash and dash!  I think it's an infinite loop.
# zsh hangs
# trap term TERM

term() {
  kill 0  # terminates the current process group
}

main() {
  local background=${1:-}

  if test -n "$background"; then
    # shouldn't wait for this to finish!
    sleep 3 &
  fi

  if false; then
    {
      while true; do
        echo ___
        sleep 0.2
      done 
    } &
  fi

  echo 'MAIN'
  echo foo | grep foo
  sleep 0.2
  echo 'DONE'

  term
}

trace() {
  bin/osh -O oil:basic -x $0 main "$@"
}

"$@"
