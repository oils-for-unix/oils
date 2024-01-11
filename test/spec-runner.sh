#!/usr/bin/env bash
#
# Run tests against multiple shells with the sh_spec framework.
#
# Usage:
#   test/spec-runner.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh
source test/common.sh
source test/spec-common.sh
source test/tsv-lib.sh  # $TAB

NUM_SPEC_TASKS=${NUM_SPEC_TASKS:-400}

# Option to use our xargs implementation.
#xargs() {
#  echo "Using ~/git/oilshell/xargs.py/xargs.py"
#  ~/git/oilshell/xargs.py/xargs.py "$@"
#}

#
# Test Runner
#

write-suite-manifests() {
  #test/sh_spec.py --print-table spec/*.test.sh
  { test/sh_spec.py --print-table spec/*.test.sh | while read suite name; do
      case $suite in
        osh) echo $name >& $osh ;;
        ysh) echo $name >& $ysh ;;
        tea) echo $name >& $tea ;;
        disabled) ;;  # ignore
        *)   die "Invalid suite $suite" ;;
      esac
    done 
  } {osh}>_tmp/spec/SUITE-osh.txt \
    {ysh}>_tmp/spec/SUITE-ysh.txt \
    {tea}>_tmp/spec/SUITE-tea.txt \
    {needs_terminal}>_tmp/spec/SUITE-needs-terminal.txt

  # These are kind of pseudo-suites, not the main 3
  test/sh_spec.py --print-tagged interactive \
    spec/*.test.sh > _tmp/spec/SUITE-interactive.txt

  test/sh_spec.py --print-tagged dev-minimal \
    spec/*.test.sh > _tmp/spec/SUITE-osh-minimal.txt
}


diff-manifest() {
  ### temporary test

  write-suite-manifests
  #return

  # crazy sorting, affects glob
  # doesn't work
  #LANG=C 
  #LC_COLLATE=C
  #LC_ALL=C
  #export LANG LC_COLLATE LC_ALL

  for suite in osh ysh tea interactive osh-minimal; do
    echo
    echo [$suite]
    echo

    diff -u -r <(sort spec2/SUITE-$suite.txt) <(sort _tmp/spec/SUITE-$suite.txt) #|| true
  done
}

dispatch-one() {
  # Determines what binaries to compare against: compare-py | compare-cpp | release-alpine 
  local compare_mode=${1:-compare-py}
  # Which subdir of _tmp/spec: osh-py ysh-py osh-cpp ysh-cpp smoosh tea
  local spec_subdir=${2:-osh-py}
  local spec_name=$3
  shift 3  # rest are more flags

  log "__ $spec_name"

  local -a prefix
  case $compare_mode in

    compare-py)     prefix=(test/spec.sh) ;;

    compare-cpp)    prefix=(test/spec-cpp.sh run-file) ;;

    # For interactive comparison
    osh-only)       prefix=(test/spec-util.sh run-file-with-osh) ;;
    bash-only)      prefix=(test/spec-util.sh run-file-with-bash) ;;

    release-alpine) prefix=(test/spec-alpine.sh run-file) ;;

    *) die "Invalid compare mode $compare_mode" ;;
  esac

  local base_dir=_tmp/spec/$spec_subdir

  # TODO: Could --stats-{file,template} be a separate awk step on .tsv files?
  run-task-with-status \
    $base_dir/${spec_name}.task.txt \
    "${prefix[@]}" $spec_name \
      --format html \
      --stats-file $base_dir/${spec_name}.stats.txt \
      --stats-template \
      '%(num_cases)d %(oils_num_passed)d %(oils_num_failed)d %(oils_failures_allowed)d %(oils_ALT_delta)d' \
      "$@" \
    > $base_dir/${spec_name}.html
}


_html-summary() {
  ### Print an HTML summary to stdout and return whether all tests succeeded

  local sh_label=$1  # osh or ysh
  local base_dir=$2  # e.g. _tmp/spec/ysh-cpp
  local totals=$3  # path to print HTML to
  local manifest=$4

  html-head --title "Spec Test Summary" \
    ../../../web/base.css ../../../web/spec-tests.css

  cat <<EOF
  <body class="width50">

<p id="home-link">
  <!-- The release index is two dirs up -->
  <a href="../..">Up</a> |
  <a href="/">oilshell.org</a>
</p>

<h1>Spec Test Results Summary</h1>

<table>
  <thead>
  <tr>
    <td>name</td>
    <td># cases</td> <td>$sh_label # passed</td> <td>$sh_label # failed</td>
    <td>$sh_label failures allowed</td>
    <td>$sh_label ALT delta</td>
    <td>Elapsed Seconds</td>
  </tr>
  </thead>
  <!-- TOTALS -->
EOF

  # Awk notes:
  # - "getline" is kind of like bash "read", but it doesn't allow you do
  # specify variable names.  You have to destructure it yourself.
  # - Lack of string interpolation is very annoying

  head -n $NUM_SPEC_TASKS $manifest | sort | awk -v totals=$totals -v base_dir=$base_dir '
  # Awk problem: getline errors are ignored by default!
  function error(path) {
    print "Error reading line from file: " path > "/dev/stderr"
    exit(1)
  }

  {
    spec_name = $0

    # Read from the task files
    path = ( base_dir "/" spec_name ".task.txt" )
    n = getline < path
    if (n != 1) {
      error(path)
    }
    status = $1
    wall_secs = $2

    path = ( base_dir "/" spec_name ".stats.txt" )
    n = getline < path
    if (n != 1) {
      error(path)
    }
    num_cases = $1
    oils_num_passed = $2
    oils_num_failed = $3
    oils_failures_allowed = $4
    oils_ALT_delta = $5

    sum_status += status
    sum_wall_secs += wall_secs
    sum_num_cases += num_cases
    sum_oils_num_passed += oils_num_passed
    sum_oils_num_failed += oils_num_failed
    sum_oils_failures_allowed += oils_failures_allowed
    sum_oils_ALT_delta += oils_ALT_delta
    num_rows += 1

    # For the console
    if (status == 0) {
      num_passed += 1
    } else {
      num_failed += 1
      print spec_name " failed with status " status > "/dev/stderr"
    }

    if (status != 0) {
      css_class = "failed"
    } else if (oils_num_failed != 0) {
      css_class = "osh-allow-fail"
    } else if (oils_num_passed != 0) {
      css_class = "osh-pass"
    } else {
      css_class = ""
    }
    print "<tr class=" css_class ">"
    print "<td><a href=" spec_name ".html>" spec_name "</a></td>"
    print "<td>" num_cases "</td>"
    print "<td>" oils_num_passed "</td>"
    print "<td>" oils_num_failed "</td>"
    print "<td>" oils_failures_allowed "</td>"
    print "<td>" oils_ALT_delta "</td>"
    printf("<td>%.2f</td>\n", wall_secs);
    print "</tr>"
  }

  END {
    print "<tr class=totals>" >totals
    print "<td>TOTAL (" num_rows " rows) </td>" >totals
    print "<td>" sum_num_cases "</td>" >totals
    print "<td>" sum_oils_num_passed "</td>" >totals
    print "<td>" sum_oils_num_failed "</td>" >totals
    print "<td>" sum_oils_failures_allowed "</td>" >totals
    print "<td>" sum_oils_ALT_delta "</td>" >totals
    printf("<td>%.2f</td>\n", sum_wall_secs) > totals
    print "</tr>" >totals

    print "<tfoot>"
    print "<!-- TOTALS -->"
    print "</tfoot>"

    # For the console
    print "" > "/dev/stderr"
    if (num_failed == 0) {
      print "*** All " num_passed " tests PASSED" > "/dev/stderr"
    } else {
      print "*** " num_failed " tests FAILED" > "/dev/stderr"
      exit(1)  # failure
  }
  }
  '
  all_passed=$?

  cat <<EOF
    </table>

    <h3>Version Information</h3>
    <pre>
EOF

  # TODO: can pass shells here, e.g. for test/spec-cpp.sh
  test/spec-version.sh ${suite}-version-text

  cat <<EOF
    </pre>
  </body>
</html>
EOF

  return $all_passed
}

html-summary() {
  local suite=$1
  local base_dir=$2

  local manifest="_tmp/spec/SUITE-$suite.txt"

  local totals=$base_dir/totals-$suite.html
  local tmp=$base_dir/tmp-$suite.html

  local out=$base_dir/index.html

  # TODO: Do we also need $base_dir/{osh,oil}-details-for-toil.json
  # osh failures, and all failures
  # When deploying, if they exist, them copy them outside?
  # I guess toil_web.py can use the zipfile module?
  # To get _tmp/spec/...
  # it can read JSON like:
  # { "task_tsv": "_tmp/toil/INDEX.tsv",
  #   "details_json": [ ... ],
  # }

  set +o errexit
  _html-summary $suite $base_dir $totals $manifest > $tmp
  all_passed=$?
  set -o errexit

  # Total rows are displayed at both the top and bottom.
  awk -v totals="$(cat $totals)" '
  /<!-- TOTALS -->/ {
    print totals
    next
  }
  { print }
  ' < $tmp > $out

  echo
  echo "Results: file://$PWD/$out"

  return $all_passed
}

_all-parallel() {
  local suite=${1:-osh}
  local compare_mode=${2:-compare-py}
  local spec_subdir=${3:-survey}

  # The rest are more flags
  shift 3

  local manifest="_tmp/spec/SUITE-$suite.txt"
  local output_base_dir="_tmp/spec/$spec_subdir"
  mkdir -p $output_base_dir

  write-suite-manifests

  # The exit codes are recorded in files for html-summary to aggregate.
  set +o errexit
  head -n $NUM_SPEC_TASKS $manifest \
    | xargs -I {} -P $MAX_PROCS -- \
      $0 dispatch-one $compare_mode $spec_subdir {} "$@"
  set -o errexit

  all-tests-to-html $manifest $output_base_dir

  # note: the HTML links to ../../web/, which is in the repo.
  html-summary $suite $output_base_dir  # returns whether all passed
}

all-parallel() {
  ### Run spec tests in parallel.

  # Note that this function doesn't fail because 'run-file' saves the status
  # to a file.

  time $0 _all-parallel "$@"
}

all-tests-to-html() {
  local manifest=$1
  local output_base_dir=$2
  # ignore attrs output
  head -n $NUM_SPEC_TASKS $manifest \
    | xargs --verbose -- doctools/src_tree.py spec-files $output_base_dir >/dev/null

    #| xargs -n 1 -P $MAX_PROCS -- $0 test-to-html $output_base_dir
  log "done: all-tests-to-html"
}

shell-sanity-check() {
  echo "PWD = $PWD"
  echo "PATH = $PATH"

  for sh in "$@"; do
    # note: shells are in $PATH, but not $OSH_LIST
    if ! $sh -c 'echo -n "hello from $0: "; command -v $0 || true'; then 
      echo "ERROR: $sh failed sanity check"
      return 1
    fi
  done
}

filename=$(basename $0)
if test "$filename" = 'spec-runner.sh'; then
  "$@"
fi
