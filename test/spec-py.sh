#!/usr/bin/env bash
#
# Compare Python implementation with other shells.
#
# Contrast with test/spec-cpp.sh, which compares the Python and C++ version.
#
# Usage:
#   test/spec-py.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/spec-common.sh

check-survey-shells() {
  ### Make sure bash, zsh, OSH, etc. exist

  # Note: yash isn't here, but it is used in a couple tests

  test/spec-runner.sh shell-sanity-check dash bash mksh zsh ash $OSH_LIST
}

run-file() {
  local spec_name=$1
  shift

  sh-spec spec/$spec_name.test.sh \
    --compare-shells \
    --oils-bin-dir $PWD/bin "$@"
}

osh-all() {
  check-survey-shells

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
  version=$(head -n 1 oils-version.txt)

  local tar_root=$REPO_ROOT/_tmp/oils-ref-tar-test/oils-ref-$version

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

osh-minimal() {
  ### Some tests that work on the minimal build.  Run by Soil.

  # depends on link-busybox-ash, then source dev-shell.sh at the top of this
  # file
  check-survey-shells

  # suite compare_mode spec_subdir
  test/spec-runner.sh all-parallel osh-minimal compare-py osh-minimal "$@"
}


osh-all-serial() { MAX_PROCS=1 $0 osh-all "$@"; }
ysh-all-serial() { MAX_PROCS=1 $0 ysh-all "$@"; }
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
  smoosh-html "${more_flags[@]}"
  smoosh-hang-html "${more_flags[@]}"
}

#
# Smoosh
#

readonly SMOOSH_REPO=~/git/languages/smoosh

sh-spec-smoosh-env() {
  local test_file=$1
  shift

  # - smoosh tests use $TEST_SHELL instead of $SH
  # - cd $TMP to avoid littering repo
  # - pass -o posix
  # - timeout of 1 second
  # - Some tests in smoosh use $HOME and $LOGNAME

  sh-spec $test_file \
    --sh-env-var-name TEST_SHELL \
    --posix \
    --env-pair "TEST_UTIL=$SMOOSH_REPO/tests/util" \
    --env-pair "LOGNAME=$LOGNAME" \
    --env-pair "HOME=$HOME" \
    --timeout 1 \
    --oils-bin-dir $REPO_ROOT/bin \
    --compare-shells \
    "$@"
}

# For speed, only run with one copy of OSH.
readonly smoosh_osh_list=$OSH_CPYTHON

smoosh() {
  ### Run case smoosh from the console

  # TODO: Use --oils-bin-dir
  # our_shells, etc.

  sh-spec-smoosh-env _tmp/smoosh.test.sh \
    dash bash mksh $smoosh_osh_list \
    "$@"
}

smoosh-hang() {
  ### Run case smoosh-hang from the console

  # Need the smoosh timeout tool to run correctly.
  sh-spec-smoosh-env _tmp/smoosh-hang.test.sh \
    --timeout-bin "$SMOOSH_REPO/tests/util/timeout" \
    --timeout 1 \
    "$@"
}

_one-html() {
  local spec_name=$1
  shift

  local out_dir=_tmp/spec/smoosh
  local tmp_dir=_tmp/src-smoosh
  mkdir -p $out_dir $out_dir

  PYTHONPATH='.:vendor' doctools/src_tree.py smoosh-file \
    _tmp/$spec_name.test.sh \
    $out_dir/$spec_name.test.html

  local out=$out_dir/${spec_name}.html
  set +o errexit
  # Shell function is smoosh or smoosh-hang
  time $spec_name --format html "$@" > $out
  set -o errexit

  echo
  echo "Wrote $out"

  # NOTE: This IGNORES the exit status.
}

# TODO:
# - Put these tests in the CI
# - Import smoosh spec tests into the repo, with 'test/smoosh.sh'

smoosh-html() {
  ### Run by devtools/release.sh
  _one-html smoosh "$@"
}

smoosh-hang-html() {
  ### Run by devtools/release.sh
  _one-html smoosh-hang "$@"
}

html-demo() {
  ### Test for --format html

  local out=_tmp/spec/demo.html
  builtin-special --format html "$@" > $out

  echo
  echo "Wrote $out"
}


#
# Misc
#

# Really what I want is enter(func) and exit(func), and filter by regex?
trace-var-sub() {
  local out=_tmp/coverage
  mkdir -p $out

  # This creates *.cover files, with line counts.
  #python -m trace --count -C $out \

  # This prints trace with line numbers to stdout.
  #python -m trace --trace -C $out \
  PYTHONPATH=. python -m trace --trackcalls -C $out \
    test/sh_spec.py spec/var-sub.test.sh dash bash "$@"

  ls -l $out
  head $out/*.cover
}

task-five "$@"
