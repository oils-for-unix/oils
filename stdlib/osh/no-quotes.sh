#!/usr/bin/env bash
#
# Testing library for bash and OSH.
#
# Capture status/stdout/stderr, and nq-assert those values.

source stdlib/osh/two.sh

nq-assert() {
  ### Must be run with errexit off

  if ! test "$@"; then
    die "line ${BASH_LINENO[0]}: nq-assert '$@' failed"
  fi
}

nq-capture() {
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

nq-capture-2() {
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

test-nq-capture() {
  local status stdout
  nq-capture status stdout \
    echo hi

  nq-assert 0 = "$status"
  nq-assert 'hi' = "$stdout"

  local stderr
  nq-capture-2 status stderr \
    _demo-stderr yyy

  #echo "stderr: [$stderr]"

  nq-assert 99 = "$status"
  nq-assert 'zzz yyy' = "$stderr"

  nq-capture status stdout \
    _demo-stderr aaa

  #echo "stderr: [$stderr]"

  nq-assert 99 = "$status"
  nq-assert '' = "$stdout"
}

name=$(basename $0)
if test "$name" = 'testing.sh'; then
  "$@"
fi
