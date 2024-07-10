#!/usr/bin/env bash
#
# Test the C++ translation of Oils.
#
# Usage:
#   test/spec-cpp.sh <function name>
#
# Examples:
#   test/spec-cpp.sh run-file smoke -r 0 -v
#   NUM_SPEC_TASKS=2 test/spec-cpp.sh osh-all

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # PYTHONPATH
source devtools/task-five.sh
source test/common.sh  # html-head
source test/spec-common.sh
source web/table/html.sh

shopt -s failglob  # to debug TSV expansion failure below

OSH_PY=$REPO_ROOT/bin/osh
YSH_PY=$REPO_ROOT/bin/ysh

# Run with ASAN binary by default.  Release overrides this
OSH_CC=${OSH_CC:-$REPO_ROOT/_bin/cxx-asan/osh}
YSH_CC=${YSH_CC:-$REPO_ROOT/_bin/cxx-asan/ysh}

# Same variable in test/spec-runner.sh
NUM_SPEC_TASKS=${NUM_SPEC_TASKS:-400}

# So we can pass ASAN.  Note that test/spec-common.sh has to pass this to
# sh_spec.py.
export OILS_GC_ON_EXIT=1

#
# For translation
#

run-file() {
  local spec_name=$1
  shift

  local spec_file=spec/$spec_name.test.sh

  local suite
  suite=$(test/sh_spec.py --print-spec-suite $spec_file)

  local spec_subdir
  case $suite in
    osh) spec_subdir='osh-cpp' ;;
    ysh) spec_subdir='ysh-cpp' ;;
    *)   die "Invalid suite $suite" ;;
  esac

  local base_dir=_tmp/spec/$spec_subdir
  mkdir -v -p $base_dir

  # Compare Python and C++ shells by passing --oils-cpp-bin-dir
  sh-spec $spec_file \
    --timeout 10 \
    --oils-bin-dir $PWD/bin \
    --oils-cpp-bin-dir $REPO_ROOT/_bin/cxx-asan \
    --tsv-output $base_dir/${spec_name}.tsv \
    "$@"
}

osh-all() {
  # Like test/spec.sh {osh,ysh}-all, but it compares against different binaries

  # For debugging hangs
  #export MAX_PROCS=1

  ninja _bin/cxx-asan/{osh,ysh}

  test/spec-runner.sh shell-sanity-check $OSH_PY $OSH_CC

  local spec_subdir=osh-cpp 

  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    osh compare-cpp $spec_subdir "$@" || true  # OK if it fails

  write-compare-html $spec_subdir
}

ysh-all() {
  ninja _bin/cxx-asan/{osh,ysh}

  local spec_subdir=ysh-cpp 

  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    ysh compare-cpp $spec_subdir "$@" || true  # OK if it fails

  write-compare-html $spec_subdir
}

console-row() {
  ### Print out a histogram of results

  awk '
FNR == 1 {
  #print FILENAME > "/dev/stderr" 
}
FNR != 1 {
  case_num = $1
  sh = $2
  result = $3

  if (sh == "osh") {
    osh[result] += 1
  } else if (sh == "osh_cpp") {  # bin/osh_cpp
    oe_py[result] += 1
  } else if (sh == "osh_ALT") {  # _bin/*/osh
    oe_cpp[result] += 1
  }
}

function print_hist(sh, hist) {
  printf("%s\t", sh)

  k = "pass"
  printf("%s %4d\t", k, hist[k])
  k = "FAIL"
  printf("%s %4d\t", k, hist[k])

  print ""

  # This prints N-I, ok, bug, etc.
  #for (k in hist) {
  #  printf("%s %s\t", k, hist[k])
  #}

}

END { 
  print_hist("osh", osh)
  print_hist("osh_cpp", oe_py)
  print_hist("osh_ALT", oe_cpp)
}
  ' "$@"
}

console-summary() {
  ### Report on our progress translating

  local spec_subdir=$1

  # Can't go at the top level because files won't exist!
  readonly TSV=(_tmp/spec/$spec_subdir/*.tsv)

  wc -l "${TSV[@]}"

  for file in "${TSV[@]}"; do
    echo
    echo "$file"
    console-row $file
  done

  echo
  echo "TOTAL"
  console-row "${TSV[@]}"
}

#
# HTML
#

summary-csv-row() {
  ### Print one row or the last total row

  local spec_subdir=$1
  shift

  if test $# -eq 1; then
    local spec_name=$1
    local -a tsv_files=( _tmp/spec/$spec_subdir/$spec_name.tsv )
  else
    local spec_name='TOTAL'
    local -a tsv_files=( "$@" )
  fi

  awk -v spec_name=$spec_name '
# skip the first row
FNR != 1 {
  case_num = $1
  sh = $2
  result = $3

  if (sh == "osh" || sh == "ysh") {
    osh[result] += 1
  } else if (sh == "osh-cpp" || sh == "ysh-cpp") {  # bin/osh
    osh_native[result] += 1
  }
}

END { 
  num_py = osh["pass"]
  num_cpp = osh_native["pass"] 
  if (spec_name == "TOTAL") {
    href = ""
  } else {
    href = sprintf("%s.html", spec_name)
  }

  if (num_py == num_cpp) {
    row_css_class = "cpp-good"  # green
  }

  printf("%s,%s,%s,%d,%d,%d\n",
         row_css_class,
         spec_name, href,
         num_py,
         num_cpp,
         num_py - num_cpp)
}
' "${tsv_files[@]}"
}

summary-csv() {
  local spec_subdir=$1

  local sh_label
  local manifest

  case $spec_subdir in
    osh-cpp)
      sh_label=osh
      manifest=_tmp/spec/SUITE-osh.txt
      ;;
    ysh-cpp)
      sh_label=ysh
      manifest=_tmp/spec/SUITE-ysh.txt
      ;;
    *)
      die "Invalid dir $spec_subdir"
      ;;
  esac

  # Can't go at the top level because files might not exist!
  cat <<EOF
ROW_CSS_CLASS,name,name_HREF,${sh_label}_py,${sh_label}_cpp,delta
EOF

  # total row rows goes at the TOP, so it's in <thead> and not sorted.
  summary-csv-row $spec_subdir _tmp/spec/$spec_subdir/*.tsv

  head -n $NUM_SPEC_TASKS $manifest | sort |
  while read spec_name; do
    summary-csv-row $spec_subdir $spec_name
  done 
}

html-summary-header() {
  local prefix=../../..
  html-head --title 'Passing Spec Tests in C++' \
    $prefix/web/ajax.js \
    $prefix/web/table/table-sort.js $prefix/web/table/table-sort.css \
    $prefix/web/base.css \
    $prefix/web/spec-cpp.css

  table-sort-begin "width50"

  cat <<EOF
<p id="home-link">
  <!-- The release index is two dirs up -->
  <a href="../..">Up</a> |
  <a href="/">oilshell.org</a>
</p>

<h1>Python vs C++</h1>

<p>These numbers measure the progress of the C++ translation.
Compare with <a href=".">index.html</a>.
</p>

EOF
}

html-summary-footer() {
  cat <<EOF
<p>Generated by <code>test/spec-cpp.sh</code>.</p>
EOF
  table-sort-end 'summary'  # The table name
}

# TODO: Use here-schema-tsv in test/tsv-lib.sh
here-schema() {
  ### Read a legible text format on stdin, and write CSV on stdout

  # This is a little like: https://wiki.xxiivv.com/site/tablatal.html
  # TODO: generalize this in stdlib/here.sh
  while read one two; do
    echo "$one,$two"
  done
}

write-compare-html() {
  local spec_subdir=$1

  local sh_label
  case $spec_subdir in
    osh-cpp)
      sh_label=osh
      ;;
    ysh-cpp)
      sh_label=ysh
      ;;
    *)
      die "Invalid dir $spec_subdir"
      ;;
  esac

  local dir=_tmp/spec/$spec_subdir
  local out=$dir/compare.html

  summary-csv $spec_subdir >$dir/summary.csv 

  # The underscores are stripped when we don't want them to be!
  # Note: we could also put "pretty_heading" in the schema

  here-schema >$dir/summary.schema.csv <<EOF
column_name     type
ROW_CSS_CLASS   string
name            string
name_HREF       string
${sh_label}_py  integer
${sh_label}_cpp integer
delta           integer
EOF

  { html-summary-header
    # total row isn't sorted
    web/table/csv2html.py --thead-offset 1 $dir/summary.csv
    html-summary-footer
  } > $out

  log "Comparison: file://$REPO_ROOT/$out"
}

tsv-demo() {
  sh-spec spec/arith.test.sh --tsv-output _tmp/arith.tsv dash bash "$@"
  cat _tmp/arith.tsv
}

repro() {
  test/spec.sh alias -r 0 -p > _tmp/a
  ninja _bin/clang-dbg/osh
  _bin/clang-dbg/osh _tmp/a
}

repro-all() {
  OSH_CC=$REPO_ROOT/_bin/clang-dbg/osh $0 all
}

task-five "$@"
