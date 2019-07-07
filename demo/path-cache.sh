#!/bin/bash
#
# Test how many calls to execve() there are.
# This is also a good demo of extraneous stat() calls at startup!  bash has a
# bunch.
#
# Usage:
#   ./path-cache.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

sh-demo() {
  local sh=$1
  local syscalls='execve,stat,lstat,access'
  #local syscalls='execve'
  strace -ff -e $syscalls  -- $sh -c 'whoami; whoami'
}

main() {
  for sh in dash bash bin/osh; do
    echo $'\t---'
    echo $'\t'$sh
    echo $'\t---'

    sh-demo $sh
  done
}

"$@"
