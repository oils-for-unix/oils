#!/usr/bin/env bash
#
# Usage:
#   test/group-session.sh <function name>

set -o errexit

source test/common.sh

test-fgproc() {
  test/group-session-runner.sh run_with_shell bin/osh fgproc
}

test-fgproc-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh fgproc
}

test-bgproc() {
  test/group-session-runner.sh run_with_shell bin/osh bgproc
}

test-bgproc-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh bgproc
}

test-fgpipe() {
  test/group-session-runner.sh run_with_shell bin/osh fgpipe
}

test-fgpipe-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh fgpipe
}

test-bgpipe() {
  test/group-session-runner.sh run_with_shell bin/osh bgpipe
}

test-bgpipe-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh bgpipe
}

test-subshell() {
  test/group-session-runner.sh run_with_shell bin/osh subshell
}

test-subshell-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh subshell
}

test-csub() {
  test/group-session-runner.sh run_with_shell bin/osh csub
}

test-csub-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh csub
}

test-psub() {
  test/group-session-runner.sh run_with_shell bin/osh psub
}

test-psub-interactive() {
  test/group-session-runner.sh run_with_shell_interactive bin/osh psub
}

soil-run() {
  test/group-session-runner.sh setup
  run-test-funcs
}

"$@"
