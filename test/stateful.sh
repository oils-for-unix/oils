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

source test/common.sh  # run-task-with-status

# This uses ../oil_DEPS/spec-bin/{bash,dash} if they exist

# The ovm-tarball container that has spec-bin doesn't have python3 :-(  Really
# we should build another container
source build/dev-shell.sh

export PYTHONPATH=.

readonly BASE_DIR=_tmp/stateful

signals() {
  spec/stateful/signals.py --osh-failures-allowed 1 \
    $OSH bash "$@"
}

interactive() {
  spec/stateful/interactive.py \
    $OSH bash dash "$@"
}

job-control() {
  spec/stateful/job_control.py \
    $OSH bash "$@"
}

manifest() {
  ### List all tests

  cat <<EOF
interactive
job-control
signals
EOF
}

run-file() {
  local spec_name=$1

  log "__ $spec_name"

  # could be 'test/spec-alpine.sh run-test', which WILL BE SPLIT!
  local spec_runner=${SPEC_RUNNER:-test/spec.sh}
  local base_dir=$BASE_DIR

  # TODO: Could --stats-{file,template} be a separate awk step on .tsv files?
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
  <a href="..">Up</a> |
  <a href="/">oilshell.org</a>
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

  # TODO: The reports for each file should be written and uploaded.

  set +o errexit
  manifest | xargs -n 1 -- $0 run-file
  set -o errexit

  # Returns whether all passed
  html-summary > $BASE_DIR/index.html
}

soil-run() {
  ### Run it a few times to work around flakiness

  local n=5
  echo "Running $n times"

  local num_success=0
  local status=0

  for i in $(seq $n); do
    echo -----
    echo "Iteration $i"
    echo -----

    set +o errexit

    all

    status=$?
    set -o errexit

    if test "$status" -eq 0; then
      num_success=$((num_success + 1))
    fi
    if test "$num_success" -ge 2; then
      echo "test/interactive OK: 2 of $i tries succeeded"
      return 0
    fi
  done

  # This test is flaky, so only require 2 of 5 successes
  echo "test/interactive FAIL: got $num_success successes after $n tries"
  return 1
}

"$@"
