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
source test/tsv-lib.sh

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

# Hack for testing the harness
#readonly FIRST='-r 0'
readonly FIRST=''

signals-quick() {
  spec/stateful/signals.py $FIRST \
    $OSH bash "$@"
}

# They now pass for dash and mksh, with wait -n and PIPESTATUS skipped.
# zsh doesn't work now, but could if the prompt was changed to $ ?
signals() { signals-quick dash mksh "$@"; }

interactive-quick() {
  spec/stateful/interactive.py $FIRST \
    $OSH bash "$@"
}
# Doesn't work in mksh or zsh
interactive() { interactive-quick dash "$@"; }

job-control-quick() {
  spec/stateful/job_control.py $FIRST --osh-failures-allowed 2 \
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

run-file() {
  local spec_name=$1

  log "__ $spec_name"

  # could be 'test/spec-alpine.sh run-test', which WILL BE SPLIT!
  local spec_runner=${SPEC_RUNNER:-test/spec.sh}
  local base_dir=$BASE_DIR

  local log_filename=$spec_name.log.txt
  local results_filename=$spec_name.results.txt

  time-tsv -o $base_dir/${spec_name}.task.txt \
    --field $spec_name --field $log_filename --field $results_filename -- \
    $0 $spec_name --results-file $base_dir/$results_filename \
    >$base_dir/$log_filename 2>&1 || true
}

html-summary() {
  ### Summarize all files

  # Note: In retrospect, it would be better if every process writes a "long"
  # TSV file of results.
  # And then we concatenate them and write the "wide" summary here.

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
          <td>Test File</td>
          <td>Log</td>
          <td>Elapsed seconds</td>
          <td>Status</td>
        </tr>
      </thead>
EOF

  local all_passed=0

  shopt -s lastpipe  # to mutate all_passed in while

  manifest | while read spec_name; do

    # Note: in test/spec-runner.sh, an awk script creates this table.  It reads
    # *.task.txt and *.stats.txt.  I could add --stats-file to harness.py
    # with pass/fail stats
    read status elapsed _ log_filename results_filename < $BASE_DIR/${spec_name}.task.txt

    echo '<tr>'
    echo "<td> <a href="$results_filename">$spec_name</a> </td>"
    echo "<td> <a href="$log_filename">Log</a> </td>"

    printf -v elapsed_str '%.2f' $elapsed
    echo "<td>$elapsed_str</td>"

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

  set -o errexit

  return $status
}

soil-run() {
  ### Run it a few times to work around flakiness

  all
}

"$@"
