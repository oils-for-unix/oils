#!/usr/bin/env bash
#
# Compare Python implementation with other shells.
#
# Contrast with test/spec-cpp.sh, which compares the Python and C++ version.
#
# Usage:
#   test/spec-py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/spec-common.sh
source devtools/run-task.sh

run-file() {
  local spec_name=$1
  shift

  sh-spec spec/$spec_name.test.sh \
    --compare-shells \
    --oils-bin-dir $PWD/bin "$@"
}

osh-all() {
  test/spec.sh check-survey-shells

  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel osh compare-py osh-py "$@"

  # By default, it runs sh_spec.py with --compare-shells
  # Can also add:
  #   --ovm-bin-dir
  #   --oils-cpp-bin-dir
  # to compare with more
}

ysh-all() {
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel ysh compare-py ysh-py "$@"
}

ysh-ovm-tarball() {
  ### Regression test run by CI

  local version
  version=$(head -n 1 oil-version.txt)

  local tar_root=$REPO_ROOT/_tmp/oil-tar-test/oil-$version

  pushd $tar_root
  $REPO_ROOT/devtools/bin.sh make-ovm-links
  popd

  # Run the file that depends on stdlib/

  #test/spec.sh ysh-stdlib --ovm-bin-dir $tar_root/_bin

  set +o errexit
  ysh-all-serial --ovm-bin-dir $tar_root/_bin
  local status=$?
  set +o errexit

  echo
  echo status=$status
}

ysh-stdlib-regress() {
  test/spec.sh ysh-stdlib --ovm-bin-dir $REPO_ROOT/_bin "$@"
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
  test/spec-runner.sh all-parallel osh-minimal compare-py osh-minimal "$@"
}


osh-all-serial() { MAX_PROCS=1 $0 osh-all "$@"; }
ysh-all-serial() { MAX_PROCS=1 $0 ysh-all "$@"; }
tea-all-serial() { MAX_PROCS=1 $0 tea-all "$@"; }
osh-minimal-serial() { MAX_PROCS=1 $0 osh-minimal "$@"; }

interactive-osh() {
  ### Run spec files tagged 'interactive' in soil/interactive, which uses a terminal
  # This repeats what 'compare-py' does.

  # Doesn't seem to trigger "Stopped" bug, but it hangs in the CI unless serial

  # pass '1' to make it serial.  default is N-1 CPUS in test/spec-common.sh
  local max_procs=${1:-1}

  # Note: without MAX_PROCS=1, I observed at least 2 instances of hanging (for
  # 30 minutes)
  #
  # TODO:
  # - better diagnostics from those hanging instances
  #   - note: worked OK (failed to hang) one time in soil/host-shim.sh local-test-uke
  # - I suspect job control, we need to test it more throoughly, by simulating
  #   the kernel in Python unit tests

  # $suite $compare_mode $spec_subdir
  MAX_PROCS=$max_procs test/spec-runner.sh all-parallel \
    interactive osh-only interactive-osh "$@"
}

debug-2023-06() {
  # 2023-06-30: 
  # HANGING BUG after removing test/spec_param.py, and using run-file
  # All of the sudden test/spec-py.sh interactive-osh hangs in Docker, and then
  # this does too
  # It reproduces LOCALLY as well
  # But doesn't reproduce outside the container on my machine
  #
  # I get an ORPHANED bash -i command running at 100%, outside the container
  # Remember that runs with docker -t

  # NARROWED DOWN: the bug was that bash ALWAYS fails inside the container
  #
  # We don't run with bash and a terminal in the CI

  test/spec.sh run-file-with-osh builtin-history
}

interactive-bash() {
  # Triggers the "Stopped" bug with bash alone, unless max_procs=1

  # pass '1' to make it serial.  default is N-1 CPUS in test/spec-common.sh
  local max_procs=${1:-}

  # $suite $compare_mode $spec_subdir
  MAX_PROCS=$max_procs test/spec-runner.sh all-parallel \
    interactive bash-only interactive-bash "$@"
}

interactive-osh-bash() {
  # Triggers the "Stopped" bug with osh and bash!

  # Note: there's no longer a way to run with 2 shells?  We could do
  # test/sh_spec.py --shells-from-argv foo.test.sh osh bash
  echo TODO
}

all-and-smoosh() {
  ### Published with each release

  # Args are flags to sh_spec.py
  #   --oils-bin-dir
  #   --ovm-bin-dir
  local -a more_flags=( "$@" )

  # Note: MAX_PROCS=1 prevents [#oil-dev > Random Spec Test Stoppages]
  # Still need to fix that bug
  MAX_PROCS=1 osh-all "${more_flags[@]}"
  ysh-all "${more_flags[@]}"

  # These aren't all green/yellow yet, and are slow.
  test/spec.sh smoosh-html "${more_flags[@]}"
  test/spec.sh smoosh-hang-html "${more_flags[@]}"
}

run-task "$@"
