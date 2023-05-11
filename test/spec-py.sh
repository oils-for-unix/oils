#!/usr/bin/env bash
#
# Compare Python implementation with other shells.
#
# Contrast with test/spec-cpp.sh, which compares the Python adn C++ version.
#
# Usage:
#   test/spec-py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/run-task.sh

osh-all() {
  test/spec.sh check-survey-shells

  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel osh compare-py osh-py
}

oil-all() {
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel oil compare-py oil-py
}

tea-all() {
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel tea compare-py tea
}

osh-minimal() {
  ### Some tests that work on the minimal build.  Run by Soil.

  # depends on link-busybox-ash, then source dev-shell.sh at the top of this
  # file
  test/spec.sh check-survey-shells

  # suite compare_mode spec_subdir
  test/spec-runner.sh all-parallel osh-minimal compare-py osh-minimal
}


osh-all-serial() { MAX_PROCS=1 $0 osh-all "$@"; }
oil-all-serial() { MAX_PROCS=1 $0 oil-all "$@"; }
tea-all-serial() { MAX_PROCS=1 $0 tea-all "$@"; }
osh-minimal-serial() { MAX_PROCS=1 $0 osh-minimal "$@"; }

interactive-osh() {
  # pass '1' to make it serial.  default is N-1 CPUS in test/spec-common.sh
  local max_procs=${1:-}

  # Note: without MAX_PROCS=1, I observed at least 2 instances of hanging (for
  # 30 minutes)
  #
  # TODO:
  # - better diagnostics from those hanging instances
  #   - note: worked OK (failed to hang) one time in soil/host-shim.sh local-test-uke
  # - I suspect job control, we need to test it more throoughly, by simulating
  #   the kernel in Python unit tests

  # $suite $compare_mode $spec_subdir
  MAX_PROCS=$max_procs test/spec-runner.sh all-parallel interactive osh-only interactive-osh
}

interactive-bash() {
  # pass '1' to make it serial.  default is N-1 CPUS in test/spec-common.sh
  local max_procs=${1:-}

  # $suite $compare_mode $spec_subdir
  MAX_PROCS=$max_procs test/spec-runner.sh all-parallel interactive bash-only interactive-bash
}


interactive-osh-bash() {
  ### Triggers the "Stopped" bug with osh and bash!

  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel interactive osh-bash interactive-osh-bash
}

all-and-smoosh() {
  ### Published with each release

  # Note: MAX_PROCS=1 prevents [#oil-dev > Random Spec Test Stoppages]
  # Still need to fix that bug
  MAX_PROCS=1 osh-all
  oil-all

  # These aren't all green/yellow yet, and are slow.
  test/spec.sh smoosh-html
  test/spec.sh smoosh-hang-html
}

run-task "$@"
