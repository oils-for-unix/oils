#!/usr/bin/env bash
#
# Wrapper for test cases in spec/stateful
#
# Usage:
#   test/stateful.sh <function name>
#
# Examples:
#
#   test/stateful.sh all
#   test/stateful.sh signals -r 0-1   # run a range of tests
#   test/stateful.sh signals --list   # list tests

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # log

# This uses ../oil_DEPS/spec-bin/{bash,dash} if they exist
# The ovm-tarball container that has spec-bin doesn't have python3 :-(  Really
# we should build another container
source build/dev-shell.sh

export PYTHONPATH=.

readonly BASE_DIR=_tmp/stateful

run() {
  ### for PYTHONPATH
  "$@"
}

signals-quick() {
  spec/stateful/signals.py \
    $OSH bash "$@"

}
# They now pass for dash and mksh, with wait -n and PIPESTATUS skipped.
# zsh doesn't work now, but could if the prompt was changed to $ ?
signals() { signals-quick dash mksh "$@"; }

interactive-quick() {
  spec/stateful/interactive.py \
    $OSH bash "$@"
}
# Doesn't work in mksh or zsh
interactive() { interactive-quick dash "$@"; }

job-control-quick() {
  spec/stateful/job_control.py \
    $OSH bash "$@"
}
job-control() { job-control-quick dash "$@"; }

manifest() {
  ### List all tests

  cat <<EOF
interactive
job-control
signals
EOF
}

UNUSED_run-task-with-status() {
  ### like function in test/common.sh, but failure not suppressed
  local out_file=$1
  shift

  benchmarks/time_.py \
    --tsv \
    --output $out_file \
    -- "$@"
}

run-file() {
  local spec_name=$1

  log "__ $spec_name"

  # could be 'test/spec-alpine.sh run-test', which WILL BE SPLIT!
  local spec_runner=${SPEC_RUNNER:-test/spec.sh}
  local base_dir=$BASE_DIR

  run-task-with-status \
    $base_dir/${spec_name}.task.txt \
    $0 $spec_name | tee $base_dir/${spec_name}.log.txt
}

html-summary() {
  html-head --title 'Stateful Tests' \
    ../../web/base.css ../../web/spec-tests.css

  # Similar to test/spec-runner.sh and soil format-wwz-index

  cat <<EOF
  <body class="width50">

<p id="home-link">
  <!-- up to .wwz index -->
  <a href="../..">Up</a> |
  <a href="/">Home</a>
</p>

    <h1>Stateful Tests with <a href="//www.oilshell.org/cross-ref.html#pexpect">pexpect</a> </h1>

    <table>
      <thead>
        <tr>
          <td>Task</td>
          <td>Elapsed</td>
          <td>Status</td>
        </tr>
      </thead>
EOF

  local all_passed=0

  shopt -s lastpipe  # to mutate all_passed in while

  manifest | while read spec_name; do
    read status elapsed < $BASE_DIR/${spec_name}.task.txt
    echo '<tr>'
    echo "<td> <a href="$spec_name.log.txt">$spec_name</a> </td>"
    echo "<td>$elapsed</td>"

    case $status in
      (0)  # exit code 0 is success
        echo "  <td>$status</td>"
        ;;
      (*)  # everything else is a failure
        # Add extra text to make red stand out.
        echo "  <td class=\"fail\">status: $status</td>"

        # Mark failure
        all_passed=1
        ;;
    esac

    echo '</tr>'
  done

  cat <<EOF
    </table>
  </body>
</html>
EOF

  log "all_passed = $all_passed"

  return $all_passed
}

all() {
  ### Run all tests

  mkdir -p $BASE_DIR

  manifest | xargs -n 1 -- $0 run-file

  # Returns whether all passed
  set +o errexit
  html-summary > $BASE_DIR/index.html
  local status=$?

  # TODO:
  # If it failed, html-summary should also write
  # _tmp/stateful/failed-manifest.txt

  # Then run those to see if they succeed 2 of 4 times?  It would be nice to
  # report it all on a single table, but also not run too many times.  I guess
  # "retry number" can be another column in the table.

  set -o errexit

  return $status
}

# UNUSED since 'flaky-workaround run-task-with-status' doesn't compose correctly.
# run-task-with-status writes a file with the status and exits 0.

flaky-workaround() {
  ### If a command fails, see if it can succeed 2 out of the next 4 times

  set +o errexit

  "$@"
  local status=$?
  if test $status -eq 0; then
    return 0  # early return
  fi

  local n=4
  echo "Failed.  Retrying $n times"

  local num_success=0
  local status=0

  for i in $(seq $n); do
    echo -----
    echo "Retry number $i"
    echo -----

    "$@"
    status=$?

    if test "$status" -eq 0; then
      num_success=$((num_success + 1))
    fi
    if test "$num_success" -ge 2; then
      echo "test/interactive OK: 2 of $i tries succeeded"
      return 0
    fi
  done

  # This test is flaky, so only require 2 of 5 successes
  echo "FAIL: got $num_success successes after $n tries"

  set -o errexit

  return 1
}

soil-run() {
  ### Run it a few times to work around flakiness

  all
}

"$@"
