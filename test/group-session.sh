#!/usr/bin/env bash
#
# Usage:
#   test/group-session.sh <function name>

set -o errexit

source test/common.sh

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

soil-run() {
  test/group-session-runner.sh setup

  # TODO:
  # - Add bin/osh, _bin/cxx-dbg/osh
  # - dash and mksh also pass many tests

  for sh in bash zsh; do
    SH=$sh run-test-funcs

    # This could be QUICKLY=1
    # SH=$sh test-bgproc-interactive

    echo
    echo
  done

}

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

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh

time-tsv-issue() {
  #time-tsv -o _tmp/tsv -- $0 test-bgproc-interactive
  time-tsv -o _tmp/tsv -- $0 soil-run
}

"$@"
