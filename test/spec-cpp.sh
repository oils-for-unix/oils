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

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # PYTHONPATH
source test/common.sh  # html-head
source test/spec-common.sh
source test/tsv-lib.sh
source web/table/html.sh

shopt -s failglob  # to debug TSV expansion failure below

OSH_PY=$REPO_ROOT/bin/osh
YSH_PY=$REPO_ROOT/bin/ysh

# Run with ASAN binary by default.  Release overrides this
OSH_CC=${OSH_CC:-$REPO_ROOT/_bin/cxx-asan/osh}
YSH_CC=${YSH_CC:-$REPO_ROOT/_bin/cxx-asan/ysh}

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
    disabled) spec_subdir='disabled-cpp' ;;
    *)   die "Invalid suite $suite" ;;
  esac

  local base_dir=_tmp/spec/$spec_subdir
  mkdir -v -p $base_dir

  # Compare Python and C++ shells by passing --oils-cpp-bin-dir

  local variant='cxx-asan'
  # TODO: turning on gcalways will find more bugs
  #local variant='cxx-asan+gcalways'

  sh-spec $spec_file \
    --timeout 10 \
    --oils-bin-dir $PWD/bin \
    --oils-cpp-bin-dir $REPO_ROOT/_bin/$variant \
    --tsv-output $base_dir/${spec_name}.result.tsv \
    "$@"
}

osh-all() {
  # Like test/spec.sh {osh,ysh}-all, but it compares against different binaries

  # For debugging hangs
  #export MAX_PROCS=1

  ninja _bin/cxx-asan/{osh,ysh}

  test/spec-runner.sh shell-sanity-check $OSH_PY $OSH_CC

  local spec_subdir=osh-cpp 

  local status
  set +o errexit
  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    osh compare-cpp $spec_subdir "$@"
  status=$?
  set -o errexit

  # Write comparison even if we failed
  write-compare-html $spec_subdir

  return $status
}

ysh-all() {
  ninja _bin/cxx-asan/{osh,ysh}

  local spec_subdir=ysh-cpp 

  local status
  set +o errexit
  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    ysh compare-cpp $spec_subdir "$@"
  status=$?
  set -o errexit

  write-compare-html $spec_subdir

  return $status
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
  readonly TSV=(_tmp/spec/$spec_subdir/*.result.tsv)

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

summary-tsv-row() {
  ### Print one row or the last total row

  local spec_subdir=$1
  shift

  local status cpp_failures_allowed cpp_failures

  if test $# -eq 1; then
    local spec_name=$1
    local -a tsv_files=( _tmp/spec/$spec_subdir/$spec_name.result.tsv )
    status=$( awk '{printf $1}' "_tmp/spec/$spec_subdir/$spec_name.task.txt" )
    cpp_failures_allowed=$( awk '{printf $6}' "_tmp/spec/$spec_subdir/$spec_name.stats.txt" )
    cpp_failures=$( awk '{printf $7}' "_tmp/spec/$spec_subdir/$spec_name.stats.txt" )
  else
    local spec_name='TOTAL'
    local -a tsv_files=( "$@" )
    cpp_failures_allowed="-"
    cpp_failures="-"
    status=0
  fi

  awk -v spec_name=$spec_name -v status=$status \
      -v cpp_failures_allowed=$cpp_failures_allowed -v cpp_failures=$cpp_failures '
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

  if (status != 0) {
    row_css_class = "cpp-failed"  # red
  }

  row = sprintf("%s %s %s %d %d %d %d %d",
         row_css_class,
         spec_name, href,
         num_py,
         num_cpp,
         num_py - num_cpp,
         cpp_failures,
         cpp_failures_allowed)

  # Turn tabs into spaces - awk mutates the row!
  gsub(/ /, "\t", row)
  print row
}
' "${tsv_files[@]}"
}

summary-tsv() {
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
  #echo "ROW_CSS_CLASS,name,name_HREF,${sh_label}_py,${sh_label}_cpp,delta"
  tsv-row \
    'ROW_CSS_CLASS' 'name' 'name_HREF' ${sh_label}_py ${sh_label}_cpp 'delta' 'cpp_num_failed' 'cpp_failures_allowed'

  # total row rows goes at the TOP, so it's in <thead> and not sorted.
  summary-tsv-row $spec_subdir _tmp/spec/$spec_subdir/*.result.tsv

  head -n $NUM_SPEC_TASKS $manifest | sort |
  while read spec_name; do
    summary-tsv-row $spec_subdir $spec_name
  done 
}

html-summary-header() {
  local prefix=../../..

  spec-html-head $prefix 'Passing Spec Tests in C++'
  table-sort-begin "width50"

  echo '
<p id="home-link">
  <!-- The release index is two dirs up -->
  <a href="../..">Up</a> |
  <a href="/">oils.pub</a>
</p>

<h1>Python vs C++</h1>

<p>Here is the total number of passing tests.  TODO: we should also verify
tests that do not pass.
</p>

<p>Another view: <a href="index.html">index.html</a>.
</p>
'
}

html-summary-footer() {
  echo '
<p>Generated by <code>test/spec-cpp.sh</code>.
</p>

<p><a href="SUMMARY.tsv">Raw TSV</a>
</p>
'
  table-sort-end 'SUMMARY'  # The table name
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

  summary-tsv $spec_subdir >$dir/SUMMARY.tsv 

  # The underscores are stripped when we don't want them to be!
  # Note: we could also put "pretty_heading" in the schema

  here-schema-tsv >$dir/SUMMARY.schema.tsv <<EOF
column_name     type
ROW_CSS_CLASS   string
name            string
name_HREF       string
${sh_label}_py  integer
${sh_label}_cpp integer
cpp_num_failed integer
cpp_failures_allowed integer
delta           integer
EOF

  { html-summary-header
    # total row isn't sorted
    tsv2html --thead-offset 1 $dir/SUMMARY.tsv
    html-summary-footer
  } > $out

  log "Comparison: file://$REPO_ROOT/$out"
}

#
# Misc
#

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
