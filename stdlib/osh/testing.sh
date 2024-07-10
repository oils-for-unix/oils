#!/usr/bin/env bash
#
# Testing library for bash and OSH.
#
# Capture status/stdout/stderr, and sh-assert those values.

source stdlib/osh/two.sh

sh-assert() {
  ### Must be run with errexit off

  if ! test "$@"; then
    # old message
    # note: it's extremely weird that we use -1 and 0, but that seems to be how
    # bash works.
    #die "${BASH_SOURCE[-1]}:${BASH_LINENO[0]}: sh-assertn '$@' failed"

    die "line ${BASH_LINENO[0]}: sh-assert '$@' failed"
  fi
}

capture-command() {
  ### capture status and stdout

  local -n out_status=$1
  local -n out_stdout=$2
  shift 2

  local __status
  local __stdout

  # Tricky: turn errexit off so we can capture it, but turn it on against
  set +o errexit
  __stdout=$(set -o errexit; "$@")
  __status=$?
  set -o errexit

  out_status=$__status
  out_stdout=$__stdout
}

capture-command-2() {
  ### capture status and stderr 
  
  # This is almost identical to the above

  local -n out_status=$1
  local -n out_stderr=$2
  shift 2

  local __status
  local __stderr

  # Tricky: turn errexit off so we can capture it, but turn it on against
  set +o errexit
  __stderr=$(set -o errexit; "$@" 2>&1)
  __status=$?
  set -o errexit

  out_status=$__status
  out_stderr=$__stderr
}

_demo-stderr() {
  echo zzz "$@" >& 2
  return 99
}

test-capture-command() {
  local status stdout
  capture-command status stdout \
    echo hi

  sh-assert 0 = "$status"
  sh-assert 'hi' = "$stdout"

  local stderr
  capture-command-2 status stderr \
    _demo-stderr yyy

  #echo "stderr: [$stderr]"

  sh-assert 99 = "$status"
  sh-assert 'zzz yyy' = "$stderr"

  capture-command status stdout \
    _demo-stderr aaa

  #echo "stderr: [$stderr]"

  sh-assert 99 = "$status"
  sh-assert '' = "$stdout"
}

name=$(basename $0)
if test "$name" = 'testing.sh'; then
  "$@"
fi
