#!/usr/bin/env bash
#
# Run tests against multiple shells with the sh_spec framework.
#
# Usage:
#   test/spec-runner.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

#
# Test Runner
#

# Generate an array of all the spec tests.
_spec-manifest() {
  for t in spec/*.test.sh; do
    echo $t 
  done | gawk '
  match($0, "spec/(.*)[.]test.sh", array) {
    name = array[1]
    # Nothing passing here
    if (name == "extended-glob") next;

    # This was meant for ANTLR.
    if (name == "shell-grammar") next;

    # Just a demo
    if (name == "blog-other1") next;

    print name
  }
  '
  # only gawk does this kind of extraction
}

manifest() {
  _spec-manifest > _tmp/spec/MANIFEST.txt
}

run-cases() {
  local spec_name=$1

  run-task-with-status \
    _tmp/spec/${spec_name}.task.txt \
    test/spec.sh $spec_name \
      --format html \
      --stats-file _tmp/spec/${spec_name}.stats.txt \
      --stats-template \
      '%(num_cases)d %(osh_num_passed)d %(osh_num_failed)d %(osh_failures_allowed)d %(osh_ALT_delta)d' \
    > _tmp/spec/${spec_name}.html
}

readonly NUM_TASKS=400
#readonly NUM_TASKS=4

# TODO:
#
# - Sum columns in the table.

_html-summary() {
  # TODO: I think the style should be shared
  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <link href="../../web/spec-tests.css" rel="stylesheet">
  </head>
  <body>

<p id="home-link">
  <a href="/">oilshell.org</a>
</p>

<h1>Spec Test Results Summary</h1>

<table>
  <thead>
    <tr>
      <td>name</td> <td>Exit Code</td> <td>Elapsed Seconds</td>
      <td># cases</td> <td>osh # passed</td> <td>osh # failed</td>
      <td>osh failures allowed</td>
      <td>osh ALT delta</td>
    </tr>
  </thead>
EOF

  # Awk notes:
  # - "getline" is kind of like bash "read", but it doesn't allow you do
  # specify variable names.  You have to destructure it yourself.
  # - Lack of string interpolation is very annoying

  head -n $NUM_TASKS _tmp/spec/MANIFEST.txt | awk '
  # Awk problem: getline errors are ignored by default!
  function error(path) {
    print "Error reading line from file: " path > "/dev/stderr"
    exit(1)
  }

  {
    spec_name = $0

    # Read from the task files
    path = ( "_tmp/spec/" spec_name ".task.txt" )
    n = getline < path
    if (n != 1) {
      error(path)
    }
    status = $1
    wall_secs = $2

    path = ( "_tmp/spec/" spec_name ".stats.txt" )
    n = getline < path
    if (n != 1) {
      error(path)
    }
    num_cases = $1
    osh_num_passed = $2
    osh_num_failed = $3
    osh_failures_allowed = $4
    osh_ALT_delta = $5

    sum_status += status
    sum_wall_secs += wall_secs
    sum_num_cases += num_cases
    sum_osh_num_passed += osh_num_passed
    sum_osh_num_failed += osh_num_failed
    sum_osh_failures_allowed += osh_failures_allowed
    sum_osh_ALT_delta += osh_ALT_delta
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
    } else if (osh_num_failed != 0) {
      css_class = "osh-allow-fail"
    } else if (osh_num_passed != 0) {
      css_class = "osh-pass"
    } else {
      css_class = ""
    }
    print "<tr class=" css_class ">"
    print "<td><a href=" spec_name ".html>" spec_name "</a></td>"
    print "<td>" status "</td>"
    print "<td>" wall_secs "</td>"
    print "<td>" num_cases "</td>"
    print "<td>" osh_num_passed "</td>"
    print "<td>" osh_num_failed "</td>"
    print "<td>" osh_failures_allowed "</td>"
    print "<td>" osh_ALT_delta "</td>"
    print "</tr>"
  }

  END {
    print "<tfoot>"
    print "<tr>"
    print "<td>TOTAL (" num_rows " rows) </td>"
    print "<td>" sum_status "</td>"
    print "<td>" sum_wall_secs "</td>"
    print "<td>" sum_num_cases "</td>"
    print "<td>" sum_osh_num_passed "</td>"
    print "<td>" sum_osh_num_failed "</td>"
    print "<td>" sum_osh_failures_allowed "</td>"
    print "<td>" sum_osh_ALT_delta "</td>"
    print "</tr>"
    print "</tfoot>"

    # For the console
    print "" > "/dev/stderr"
    if (num_failed == 0) {
      print "*** All " num_passed " tests PASSED" > "/dev/stderr"
    } else {
      print "*** " num_failed " tests FAILED" > "/dev/stderr"
  }
  }
  '

  cat <<EOF
    </table>

    <h3>Version Information</h3>
    <pre>
EOF

  test/spec.sh version-text

  cat <<EOF
    </pre>
  </body>
</html>
EOF
}

html-summary() {
  _html-summary > _tmp/spec/index.html

  echo
  echo "Results: file://$PWD/_tmp/spec/index.html"
}

link-web() {
  ln -s -f --verbose $PWD/web _tmp
}

_all-parallel() {
  mkdir -p _tmp/spec

  manifest

  head -n $NUM_TASKS _tmp/spec/MANIFEST.txt \
    | xargs -n 1 -P $JOBS --verbose -- $0 run-cases || true

  #ls -l _tmp/spec

  all-tests-to-html

  link-web

  html-summary
}

# 8.5 seconds, 43 users.
all-parallel() {
  time $0 _all-parallel
}

# For debugging only: run tests serially.
all-serial() {
  mkdir -p _tmp/spec

  cat _tmp/spec/MANIFEST.txt | while read t; do
    echo $t
    # Run the wrapper function here
    test/spec.sh $t --format html > _tmp/spec/${t}.html || {
      echo "FAILED"
      exit 1
    }
  done
}

# NOTES:
# - GitHub does it with tables -- 2-columns, a cell for each number and line.
# - srcbook does it with a table of 2 CELLS, each with a <pre> block.  But it
#   - but doesn't link to individual # ones yet?

_test-to-html() {
  local spec_name=$1

  # A row per line makes sense for highlighting with ":target".

  #print "<a name=L" NR "></a>" line_num " " $0 
  #print "<span id=L" NR "></a>" line_num " " $0 "</span>"
  # Explicit PRE tag messes up Firefox formatting.
  #print "<td id=L" NR "><pre>" line "</pre></td>"

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <link href="../../web/spec-code.css" rel="stylesheet">
  </head>
  <body>
    <table>
EOF
  awk < spec/${spec_name}.test.sh '
  { 
    # & is the substitution character.  Why is \\& a literal backslash instead
    # of \&?  This changed on the gawk between Ubuntu 14.04 and 16.04.

    gsub("&", "\\&amp;");
    gsub("<", "\\&lt;");
    gsub(">", "\\&gt;");
    line_num = NR

    print "<tr>"
    print "<td class=num>" line_num "</td>"
    if ($0 ~ /^###/) {
      line = "<span class=comm3>" $0 "</span>"
    } else if ($0 ~ /^#/) {
      line = "<span class=comm1>" $0 "</span>"
    } else {
      line = $0
    }
    print "<td class=line id=L" line_num ">" line "</td>"
    print "</tr>"
  }
  '
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

test-to-html() {
  local spec_name=$1
  _test-to-html $spec_name > _tmp/spec/${spec_name}.test.html
}

all-tests-to-html() {
  head -n $NUM_TASKS _tmp/spec/MANIFEST.txt \
    | xargs -n 1 -P 8 --verbose -- $0 test-to-html || true
}

if test "$(basename $0)" = 'spec-runner.sh'; then
  "$@"
fi
