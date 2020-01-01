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

source test/common.sh

# Option to use our xargs implementation.
#xargs() {
#  echo "Using ~/git/oilshell/xargs.py/xargs.py"
#  ~/git/oilshell/xargs.py/xargs.py "$@"
#}

#
# Test Runner
#

# Generate an array of the spec test names.
_spec-names() {
  for t in spec/*.test.sh; do
    echo $t 
  done | gawk '
  match($0, "spec/(.*)[.]test.sh", array) {
    name = array[1]
    print name
  }
  '
  # only gawk does this kind of extraction

  # Oil:
  #
  # for t in spec/*.test.sh {
  #   if (t ~ / 'spec/' <.* = name> '.test.sh' /) {
  #     echo $name
  #   } else {
  #     die "Should have matched"
  #   }
  # }
}

manifest() {
  { _spec-names | while read t; do
      # file descriptors
      local oil=7
      local osh=8
      local both=9

      # First filter.
      case $t in
        # This is for file system globs.  We have tests elsewhere for the [[ case.
        (extended-glob) continue ;;
        # This was meant for ANTLR.
        (shell-grammar) continue ;;
        # Just a demo
        (blog-other1) continue ;;
      esac

      # A list of both.
      echo $t >& $both

      # Now split into two.
      case $t in
        (oil-*)
          echo $t >& $oil
          ;;
        (*)
          echo $t >& $osh
          ;;
      esac

    done 
  } 7>_tmp/spec/SUITE-oil.txt \
    8>_tmp/spec/SUITE-osh.txt \
    9>_tmp/spec/SUITE-osh-oil.txt

  # TODO: Fix bug where osh leaks descriptors 7, 8, 9 here!
  #ls -l /proc/$$/fd

  # Used to use this obscure bash syntax.  How do we do this in Oil?  Probably
  # with 'fopen :both foo.txt' builtin.

  # {oil}>_tmp/spec/SUITE-oil.txt \
  # {osh}>_tmp/spec/SUITE-osh.txt \
  # {both}>_tmp/spec/SUITE-osh-oil.txt

  #wc -l _tmp/spec/*.txt | sort -n
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


_html-summary() {
  local sh_label=$1  # osh or oil
  local totals=$2
  local manifest=${3:-_tmp/spec/MANIFEST.txt}

  html-head --title "Spec Test Summary" \
    ../../web/base.css ../../web/spec-tests.css

  cat <<EOF
  <body class="width60">

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

  head -n $NUM_TASKS $manifest | awk -v totals=$totals '
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
    print "<td>" num_cases "</td>"
    print "<td>" osh_num_passed "</td>"
    print "<td>" osh_num_failed "</td>"
    print "<td>" osh_failures_allowed "</td>"
    print "<td>" osh_ALT_delta "</td>"
    print "<td>" wall_secs "</td>"
    print "</tr>"
  }

  END {
    print "<tr class=totals>" >totals
    print "<td>TOTAL (" num_rows " rows) </td>" >totals
    print "<td>" sum_num_cases "</td>" >totals
    print "<td>" sum_osh_num_passed "</td>" >totals
    print "<td>" sum_osh_num_failed "</td>" >totals
    print "<td>" sum_osh_failures_allowed "</td>" >totals
    print "<td>" sum_osh_ALT_delta "</td>" >totals
    print "<td>" sum_wall_secs "</td>" >totals
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
  }
  }
  '

  cat <<EOF
    </table>

    <h3>Version Information</h3>
    <pre>
EOF

  test/spec.sh ${suite}-version-text

  cat <<EOF
    </pre>
  </body>
</html>
EOF
}

html-summary() {
  local suite=$1
  local manifest="_tmp/spec/SUITE-$suite.txt"

  local totals=_tmp/spec/totals-$suite.html
  local tmp=_tmp/spec/tmp-$suite.html

  local out=_tmp/spec/$suite.html

  _html-summary $suite $totals $manifest > $tmp

  awk -v totals="$(cat $totals)" '
  /<!-- TOTALS -->/ {
    print totals
    next
  }
  { print }
  ' < $tmp > $out

  echo
  echo "Results: file://$PWD/$out"
}

link-web() {
  ln -s -f --verbose $PWD/web _tmp
}

_all-parallel() {
  local suite=${1:-osh-oil}
  local manifest="_tmp/spec/SUITE-$suite.txt"

  mkdir -p _tmp/spec

  manifest

  set +o errexit
  head -n $NUM_TASKS $manifest | xargs -n 1 -P $JOBS --verbose -- $0 run-cases
  set -o errexit

  #ls -l _tmp/spec

  all-tests-to-html $manifest

  link-web

  html-summary $suite
}

all-parallel() {
  ### Run spec tests in parallel.

  # Note that this function doesn't fail because 'run-cases' saves the status
  # to a file.

  time $0 _all-parallel "$@"
}

# For debugging only: run tests serially.
# TODO: We could get rid of 'all-serial' and the 'osh-oil' suite.
all-serial() {
  mkdir -p _tmp/spec

  cat _tmp/spec/SUITE-osh-oil.txt | while read t; do
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
  local src=$1

  # A row per line makes sense for highlighting with ":target".

  #print "<a name=L" NR "></a>" line_num " " $0 
  #print "<span id=L" NR "></a>" line_num " " $0 "</span>"
  # Explicit PRE tag messes up Firefox formatting.
  #print "<td id=L" NR "><pre>" line "</pre></td>"

  html-head --title "$src code listing" \
    ../../web/base.css ../../web/spec-code.css

  cat <<EOF
  <body class="width40">
    <table>
EOF
  awk < $src '
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
  _test-to-html spec/${spec_name}.test.sh > _tmp/spec/${spec_name}.test.html
}

all-tests-to-html() {
  local manifest=$1
  head -n $NUM_TASKS $manifest \
    | xargs -n 1 -P $JOBS --verbose -- $0 test-to-html
}

filename=$(basename $0)
if test "$filename" = 'spec-runner.sh'; then
  "$@"
fi
