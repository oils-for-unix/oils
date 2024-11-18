#!/usr/bin/env bash
#
# Wrapper for test cases in spec/stateful
#
# Usage:
#   test/stateful.sh <function name>
#
# Examples:
#   test/stateful.sh signals -r 0-1               # run a range of tests
#   test/stateful.sh signals --list               # list tests
#   test/stateful.sh job-control --num-retries 0
#
#   test/stateful.sh signals-quick                # not all shells
#
#   test/stateful.sh soil-run
#
# TODO: Should have QUICKLY=1 variants

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source test/common.sh  # log, $OSH
source test/tsv-lib.sh

source build/dev-shell.sh

readonly BASE_DIR=_tmp/spec/stateful

# Hack for testing the harness
#readonly FIRST='-r 0'
readonly FIRST=''
readonly OSH_CPP=_bin/cxx-asan/osh

readonly -a QUICK_SHELLS=( $OSH bash )
readonly -a ALL_SHELLS=( $OSH $OSH_CPP bash )

#
# Suites in spec/stateful
#

signals() {
  spec/stateful/signals.py $FIRST "$@"
}

interactive() {
  spec/stateful/interactive.py $FIRST "$@"
}

job-control() {
  spec/stateful/job_control.py $FIRST --oils-failures-allowed 0 "$@"
}

bind() {
  spec/stateful/bind.py $FIRST --oils-failures-allowed 2 "$@"
}

# Run on just 2 shells

signals-quick() { signals "${QUICK_SHELLS[@]}" "$@"; }
interactive-quick() { interactive "${QUICK_SHELLS[@]}" "$@"; }
job-control-quick() { job-control "${QUICK_SHELLS[@]}" "$@"; }
bind-quick() { bind "${QUICK_SHELLS[@]}" "$@"; }

# Run on all shells we can

# They now pass for dash and mksh, with wait -n and PIPESTATUS skipped.  zsh
# doesn't work now, but could if the prompt was changed to $ ?
signals-all() { signals "${ALL_SHELLS[@]}" dash mksh "$@"; }

interactive-all() { interactive "${ALL_SHELLS[@]}" dash mksh "$@"; }

job-control-all() { job-control "${ALL_SHELLS[@]}" dash "$@"; }

# On non-bash shells, bind is either unsupported or the syntax is too different
bind-all() { bind "${ALL_SHELLS[@]}" "$@"; }


#
# More automation
#

print-tasks() {
  ### List all tests

  # TODO: 
  # - Print a table with --osh-allowed-failures and shells.  It can be filtered

  if test -n "${QUICKLY:-}"; then
    echo 'interactive'
  else
    echo 'bind'
    echo 'interactive'
    echo 'job-control'
    echo 'signals'
  fi
}

run-file() {
  ### Run a spec/stateful file, logging output

  local spec_name=$1

  log "__ $spec_name"

  local base_dir=$BASE_DIR

  local log_filename=$spec_name.log.txt
  local results_filename=$spec_name.results.txt

  time-tsv -o $base_dir/${spec_name}.task.txt \
    --field $spec_name --field $log_filename --field $results_filename -- \
    $0 "$spec_name-all" --results-file $base_dir/$results_filename \
    >$base_dir/$log_filename 2>&1 || true
}

html-summary() {
  ### Summarize all files

  # Note: In retrospect, it would be better if every process writes a "long"
  # TSV file of results.
  # And then we concatenate them and write the "wide" summary here.

  html-head --title 'Stateful Tests' \
    ../../../web/base.css ../../../web/spec-tests.css

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
          <td>Elapsed seconds</td>
          <td>Status</td>
        </tr>
      </thead>
EOF

  local all_passed=0

  shopt -s lastpipe  # to mutate all_passed in while

  local results_tmp=$BASE_DIR/results.html
  echo '' > $results_tmp  # Accumulate more here

  print-tasks | while read spec_name; do

    # Note: in test/spec-runner.sh, an awk script creates this table.  It reads
    # *.task.txt and *.stats.txt.  I could add --stats-file to harness.py
    # with pass/fail stats
    read status elapsed _ log_filename results_filename < $BASE_DIR/${spec_name}.task.txt

    echo '<tr>'
    echo "<td> <a href="$log_filename">$spec_name</a> </td>"

    printf -v elapsed_str '%.1f' $elapsed
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

    # Append to temp file
    {
      echo "<h2>$spec_name</h2>"
      echo '<pre>'
      escape-html $BASE_DIR/$results_filename
      echo '</pre>'
    } >> $results_tmp

  done
  echo '</table>'

  cat $results_tmp

  cat <<EOF
    </table>
  </body>
</html>
EOF

  log "all_passed = $all_passed"

  return $all_passed
}

soil-run() {
  ninja $OSH_CPP

  mkdir -p $BASE_DIR

  print-tasks | xargs -n 1 -- $0 run-file

  # Returns whether all passed
  html-summary > $BASE_DIR/index.html
}

#
# Debugging
#

test-stop() {
  python3 spec/stateful/harness.py test-stop demo/cpython/fork_signal_state.py
}

strace-py-fork() {
  rm -f -v _tmp/py-fork.*
  strace -ff -o _tmp/py-fork demo/cpython/fork_signal_state.py
  ls -l _tmp/py-fork.*

  # I see rt_sigaction(SIGSTP, ...) which is good
  # so yeah this seems perfectly fine -- why is it ignoring SIGTSTP?  :-(
}

"$@"
