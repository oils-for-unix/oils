#!/usr/bin/env bash
#
# See what system calls shells make for various constructs.  Similar to
# test/syscall.sh.
#
# Usage:
#   demo/compare-strace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

redir-trace() {
  ### trace relevant calls

  strace -e open,fcntl,dup2,close -- "$@"
}

redir() {
  #for sh in dash bash mksh bin/osh; do

  # hm bin/osh and zsh have too many close() calls.  I think this is the Python
  # interpreter
  for sh in dash bash mksh; do

    echo
    echo "--- $sh ---"
    echo

    #local code='exec 3>_tmp/3.txt; echo hello >&3; exec 3>&-; cat _tmp/3.txt'

    #local code='exec 4>_tmp/4.txt; echo hello >&4; exec 4>&-; cat _tmp/4.txt'
    #local code='true 2>&1'

    local code='true > _tmp/out.txt'
    redir-trace $sh -c "$code"
  done
}

job-control-trace() {
  ### trace relevant calls

  # why isn't tcsetpgrp valid?
  strace -ff -e fork,execve,setpgid -- "$@"
}

job-control() {
  #for sh in dash bash mksh bin/osh; do

  # hm bin/osh and zsh have too many close() calls.  I think this is the Python
  # interpreter
  for sh in dash bash mksh zsh; do

    echo
    echo "--- $sh ---"
    echo

    local code='ls | wc -l'
    job-control-trace $sh -i -c "$code"
  done
}

interactive() {
  local sh=dash
  local code='ls | wc -l'

  # is tcsetpgrp() an ioctl?  It takes a file descriptor.  I see setpgid() but
  # not tcsetpgrp().

  strace -c $sh -c "$code"
  echo -----
  strace -c $sh -i -c "$code"
}

"$@"
