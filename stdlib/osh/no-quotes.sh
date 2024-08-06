#!/usr/bin/env bash
#
# Testing library for bash and OSH.
#
# Capture status/stdout/stderr, and nq-assert those values.

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/two.sh

nq-assert() {
  ### Assertion with same syntax as shell 'test'

  if ! test "$@"; then
    die "line ${BASH_LINENO[0]}: nq-assert $(printf '%q ' "$@") failed"
  fi
}

# Problem: we want to capture status and stdout at the same time
#
# We use:
#
#  __stdout=$(set -o errexit; "$@")
#  __status=$?
#
# However, we lose the trailing \n, since that's how command subs work.

# Here is another possibility:
#
# shopt -s lastpipe  # need this too
# ( set -o errexit; "$@" ) | read -r -d __stdout
# __status=${PIPESTATUS[0]}
# shopt -u lastpipe
#
# But this feels complex for just the \n issue, which can be easily worked
# around.

nq-run() {
  ### capture status only

  local -n out_status=$1
  shift

  local __status

  # Tricky: turn errexit off so we can capture it, but turn it on against
  set +o errexit
  ( set -o errexit; "$@" )
  __status=$?
  set -o errexit

  out_status=$__status
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

# 'byo test' can set this?
: ${NQ_TEST_TEMP=/tmp}

nq-redir() {
  ### capture status and stdout

  local -n out_status=$1
  local -n out_stdout_file=$2
  shift 2

  local __status
  local __stdout_file=$NQ_TEST_TEMP/nq-redir-$$.txt

  # Tricky: turn errexit off so we can capture it, but turn it on against
  set +o errexit
  ( set -o errexit; "$@" ) > $__stdout_file
  __status=$?
  set -o errexit

  out_status=$__status
  out_stdout_file=$__stdout_file
}

nq-redir-2() {
  ### capture status and stdout

  local -n out_status=$1
  local -n out_stderr_file=$2
  shift 2

  local __status
  local __stderr_file=$NQ_TEST_TEMP/nq-redir-$$.txt

  # Tricky: turn errexit off so we can capture it, but turn it on against
  set +o errexit
  ( set -o errexit; "$@" ) 2> $__stderr_file
  __status=$?
  set -o errexit

  out_status=$__status
  out_stderr_file=$__stderr_file
}
