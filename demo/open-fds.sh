#!/bin/sh

# bash: descriptors 10 and 255
# osh: 3 and 4 taken: BAD

# dash: 10 and 11
# mksh: 24 25 26
# zsh: 10 11 12.  zsh somehow doesn't run this script correctly.  It's not
# POSIX I guess.

# count FDs greater than 10.  0-9 are reserved for scripts.
count_func() {
  local count=0
  local reserved=0

  local pid=$$

  # Uncomment this to show the FD table of the pipeline process!  The parent
  # doesn't change!

  #local pid=$BASHPID

  for path in /proc/$pid/fd/*; do
    echo $path
    count=$((count + 1))
    local fd=$(basename $path) 
    if test $fd -gt 2 && test $fd -lt 10; then
      reserved=$((reserved + 1))
    fi
  done

  ls -l /proc/$pid/fd

  echo "$count FDs open; $reserved are RESERVED (3-9)"
}

# What does it look like inside a redirect?  _tmp/err.txt must be open.
count_redir() {
  {
    count_func
  } 2> _tmp/err.txt
}

count_pipeline() {
  count_func | cat
}

# https://stackoverflow.com/questions/2493642/how-does-a-linux-unix-bash-script-know-its-own-pid
pid() {
  echo $$ $BASHPID | cat 
}

"$@"

