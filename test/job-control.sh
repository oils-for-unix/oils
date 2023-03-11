#!/usr/bin/env bash
#
# Tests for job control.
#
# Usage:
#   test/job-control.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)"/..; pwd)

source test/common.sh
source test/tsv-lib.sh

readonly BASE_DIR=_tmp/job-control

SH=${SH:-bin/osh}


test-fgproc() {
  test/group-session-runner.sh run_with_shell $SH fgproc
}

test-fgproc-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH fgproc
}

test-bgproc() {
  test/group-session-runner.sh run_with_shell $SH bgproc
}

test-bgproc-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH bgproc
}

test-fgpipe() {
  test/group-session-runner.sh run_with_shell $SH fgpipe
}

test-fgpipe-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH fgpipe
}

test-bgpipe() {
  test/group-session-runner.sh run_with_shell $SH bgpipe
}

test-bgpipe-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH bgpipe
}

test-subshell() {
  test/group-session-runner.sh run_with_shell $SH subshell
}

test-subshell-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH subshell
}

test-csub() {
  test/group-session-runner.sh run_with_shell $SH csub
}

test-csub-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH csub
}

test-psub() {
  test/group-session-runner.sh run_with_shell $SH psub
}

test-psub-interactive() {
  test/group-session-runner.sh run_with_shell_interactive $SH psub
}

# TODO: Add _bin/cxx-dbg/osh
# - zsh is failing in the CI?  Seems to pass locally
readonly -a SHELLS=(bash dash mksh zsh bin/osh)

print-tasks() {
  for sh in "${SHELLS[@]}"; do
    for snippet in fgproc bgproc fgpipe bgpipe subshell csub psub; do
      for interactive in - yes; do
        echo "${sh}${TAB}${snippet}${TAB}${interactive}"
      done
    done
  done
}

run-tasks() {
  local tsv_out=$1 

  while read sh snippet interactive; do

    local func
    if test $interactive = yes; then
      func=run_with_shell_interactive
    else
      func=run_with_shell
    fi

    # Suppress failure, since exit code is recorded
    time-tsv -o $tsv_out --append \
      --field $sh --field $snippet --field $interactive -- \
      test/group-session-runner.sh $func $sh $snippet || true
  done
}

nice-tsv() {
  ### like my pretty-tsv utility

  python2 -c '
from __future__ import print_function

import sys

for line in sys.stdin:
  cells = line.rstrip().split("\t")
  for cell in cells:
    print("%13s" % cell, end="")
  print()
'
}

soil-run() {
  test/group-session-runner.sh setup

  local tsv_out=$BASE_DIR/times.tsv
  mkdir -p $BASE_DIR

  time-tsv -o $tsv_out --print-header \
    --field sh --field snippet --field interactive

  print-tasks | run-tasks $tsv_out

  nice-tsv < $tsv_out

  return
}

#
# Reproduce bugs
#

timeout-issue() {
  ### For some reason bgproc-interactive conflicts with 'timeout' command

  set -x

  # doesn't hang with OSH
  timeout 900 $0 test-bgproc-interactive

  # doesn't hang
  SH=dash timeout --foreground 900 $0 test-bgproc-interactive
  SH=bash timeout --foreground 900 $0 test-bgproc-interactive

  # these both hang
  # SH=dash timeout 900 $0 test-bgproc-interactive
  # SH=bash timeout 900 $0 test-bgproc-interactive
}

time-tsv-issue() {
  #time-tsv -o _tmp/tsv -- $0 test-bgproc-interactive
  time-tsv -o _tmp/tsv -- $0 soil-run
}

"$@"
