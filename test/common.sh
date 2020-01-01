#!/bin/bash
#
# Usage:
#   source test/common.sh

# Include guard.
test -n "${__TEST_COMMON_SH:-}" && return
readonly __TEST_COMMON_SH=1


# TODO: Remove/rename this.  The release process might use the release binary
# instead of this dev binary.  test/spec.sh already has its own scheme.
# This is analogous to $OSH_OVM in benchmarks/common.sh.  
readonly OSH=${OSH:-bin/osh}

# For xargs -P in spec-runner.sh, wild-runner.sh.
readonly JOBS=$(( $(nproc) - 1 ))

readonly R_PATH=~/R  # Like PYTHONPATH, but for running R scripts

log() {
  echo "$@" 1>&2
}

die() {
  log "$@"
  exit 1
}

fail() {
  echo 'TEST FAILURE  ' "$@"
  exit 1
}

# NOTE: Could use BASH_SOURCE and so forth for a better error message.
assert() {
  test "$@" || die "'$@' failed"
}

run-task-with-status() {
  local out_file=$1
  shift

  # --quiet suppresses a warning message
  /usr/bin/env time \
    --output $out_file \
    --format '%x %e' \
    -- "$@" || true  # suppress failure

  # Hack to get around the fact that --quiet is Debian-specific:
  # http://lists.oilshell.org/pipermail/oil-dev-oilshell.org/2017-March/000012.html
  #
  # Long-term solution: our xargs should have --format.
  sed -i '/Command exited with non-zero status/d' $out_file

  # TODO: Use rows like this with oil
  # '{"status": %x, "wall_secs": %e, "user_secs": %U, "kernel_secs": %S}' \
}

run-task-with-status-test() {
  run-task-with-status _tmp/status.txt sh -c 'sleep 0.1; exit 1' || true
  cat _tmp/status.txt
  test "$(wc -l < _tmp/status.txt)" = '1' || die "Expected only one line"
}

# TODO: We should run them like $0?  To get more fine-grained reporting.
run-all() {
  for t in "$@"; do
    # fail calls 'exit 1'
    $t
    echo "OK  $t"
  done

  echo
  echo "All $0 tests passed."
}

# A quick and dirty function to show logs
run-other-suite-for-release() {
  local suite_name=$1
  local func_name=$2
  local out=${3:-_tmp/other/${suite_name}.txt}

  mkdir -p $(dirname $out)

  echo
  echo "*** Running test suite '$suite_name' ***"
  echo

  # I want to handle errors in $func_name while NOT changing its semantics.
  # This requires a separate shell interpreter starts with $0, not just a
  # separate process.  I came up with this fix in gold/errexit-confusion.sh.

  local status=0

  set +o errexit
  $0 $func_name >$out 2>&1
  status=$?  # pipefail makes this work.
  set -o errexit

  if test $status -eq 0; then
    echo
    log "Test suite '$suite_name' ran without errors.  Wrote '$out'"
  else
    echo
    die "Test suite '$suite_name' failed (running $func_name, wrote '$out')"
  fi
}

date-and-git-info() {
  date
  echo

  if test -d .git; then
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local hash=$(git rev-parse $branch)
    echo "oil repo: $hash on branch $branch"
  else
    echo "(not running from git repository)"
  fi
  echo
}

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

filename=$(basename $0)
if test "$filename" = 'common.sh'; then
  "$@"
fi
