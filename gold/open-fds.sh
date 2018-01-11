#!/bin/sh

# bash: descriptors 10 and 255
# osh: 3 and 4 taken: BAD

# dash: 10 and 11
# mksh: 24 25 26
# zsh: 10 11 12.  zsh somehow doesn't run this script correctly.  It's not
# POSIX I guess.

# count FDs greater than 10.  0-9 are reserved for scripts.
count_fds() {
  local count=0
  local reserved=0
  {
    for path in /proc/$$/fd/*; do
      echo $path
      count=$((count + 1))
      if test $(basename $path) -lt 10; then
        reserved=$((reserved + 1))
      fi
    done

    echo "$count FDs open; $reserved are RESERVED (0-9)"

  } 2> _tmp/err.txt

}

"$@"

