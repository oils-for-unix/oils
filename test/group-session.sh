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
  run-test-funcs
}

"$@"
