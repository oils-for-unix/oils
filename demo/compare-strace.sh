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

banner() {
  echo
  echo
  echo -e -n "\t"; echo "$@"
  echo 
  echo 
}

redir-strace() {
  ### trace relevant calls

  strace -e open,fcntl,dup2,close -- "$@"
}

redir() {
  #for sh in dash bash mksh bin/osh; do

  # hm bin/osh and zsh have too many close() calls.  I think this is the Python
  # interpreter
  for sh in dash bash mksh; do

    banner "$sh"

    #local code='exec 3>_tmp/3.txt; echo hello >&3; exec 3>&-; cat _tmp/3.txt'

    #local code='exec 4>_tmp/4.txt; echo hello >&4; exec 4>&-; cat _tmp/4.txt'
    #local code='true 2>&1'

    local code='true > _tmp/out.txt'
    redir-strace $sh -c "$code"
  done
}

io-strace() {
  ### trace relevant calls

  # -ff because it's a pipeline
  strace -ff -e 'open,close,fcntl,read,write' -- "$@"
}

readonly OSH_NATIVE=_bin/cxx-dbg/osh

readonly READ_SH='
{ echo "0123456789"; echo "ABCDEFGHIJ"; } |
while read -r line; do echo $line; done
'

read-builtin() {
  # RESULTS
  #
  # All shells read 1 byte at a time

  for sh in dash bash $OSH_NATIVE; do
    banner "$sh"

    io-strace $sh -c "$READ_SH"
  done
}

read-lines-from-disk-file() {
  # dash can't read this script

  # RESULTS:
  # mksh: reads 512 bytes at a time
  # bash: 80 and then 2620?
  # osh_native: using libc readline, it's 832 bytes at a time.

  # I think we can have a "regular file reader", which is different than a pipe
  # reader?

  for sh in mksh bash $OSH_NATIVE; do
    banner "$sh"

    # Run without args
    io-strace $sh $0
  done
}

read-lines-from-pipe() {
  # RESULTS: 
  # - dash does read(8192), hm
  # - mksh reads 1 byte at a time
  # - bash reads 1 byte at a time
  # - zsh reads 1 byte at a time
  # - osh_native with libc does 832 bytes at time.

  for sh in dash mksh bash zsh $OSH_NATIVE; do
    banner "$sh"

    # Run without args
    io-strace sh -c "cat testdata/osh-runtime/hello_world.sh | $sh"
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

#
# Translation tests
#

readonly BASE_DIR=_tmp/strace

_compare-native() {
  local code=$1

  rm -r -f -v $BASE_DIR
  mkdir -p $BASE_DIR

  ninja $OSH_NATIVE

  strace -ff -o $BASE_DIR/py -- bin/osh -c "$code"
  strace -ff -o $BASE_DIR/cpp -- $OSH_NATIVE -c "$code"

  wc -l $BASE_DIR/*
}

native-command-sub() {
  _compare-native 'echo $(echo hi)'
}

native-redirect() {
  _compare-native 'echo hi > _tmp/redir'
}

native-read-builtin() {
  _compare-native "$READ_SH"
}

if test $# -eq 0; then
  echo "$0: expected arguments"
else
  "$@"
fi
