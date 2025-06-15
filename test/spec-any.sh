#!/usr/bin/env bash
#
# Test OSH against any shell
#
# Usage:
#   test/spec-any.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh
source test/spec-common.sh
source test/tsv-lib.sh  # tsv-row
source web/table/html.sh  # table-sort-begin

OSH_TARGET=_bin/cxx-asan/osh
OSH=$PWD/$OSH_TARGET

# To compare against:
# - toysh
# - brush
# - rusty_bash
# - ksh93 - Debian package

# Metrics
# - binary size - stripped
# - lines of source code - I think we get this from DWARF debug info
#   - https://claude.ai/chat/40597e2e-4d1e-42b4-a756-7a265f01cc5a shows options
#   - llvm-dwarfdump
#   - Python lib https://github.com/eliben/pyelftools/
#   - right now this isn't worth it - spec tests are more important
# - unsafe functions / methods?
#   - cargo geiger is also hard to parse

readonly TOYBOX_DIR=~/src/toybox-0.8.12

readonly SUSH_DIR=../../shells/rusty_bash
readonly BRUSH_DIR=../../shells/brush

readonly SUSH=$PWD/$SUSH_DIR/target/release/sush 
readonly BRUSH=$PWD/$BRUSH_DIR/target/release/brush

# these are all roughly ksh compatible
readonly -a SHELLS=(bash mksh ksh $TOYBOX_DIR/sh $SUSH $BRUSH $OSH)

readonly -a SH_LABELS=(bash mksh ksh toysh sush brush osh)

download-toybox() {
  #mkdir -p ~/src
  wget --directory ~/src --no-clobber \
    https://landley.net/toybox/downloads/toybox-0.8.12.tar.gz
}

build-toybox() {
  pushd $TOYBOX_DIR

  make toybox
  # warning: using unfinished code
  make sh

  popd
}

update-rust() {
  . ~/.cargo/env
  time rustup update
}

build-brush() {
  pushd ../../shells/brush

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 3.8 seconds
  # - release: 1:06 minutes !
  # touch brush-core/src/shell.rs

  # 41s
  time cargo build
  echo

  # 1m 49s
  # It builds a stripped binary by default - disable that for metrics
  RUSTFLAGS='-C strip=none' time cargo build --release
  echo

  popd
}

build-sush() {
  pushd ../../shells/rusty_bash

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 1 second
  # - release: 6 seconds
  #touch src/core.rs

  # 10 seconds
  time cargo build
  echo

  # 15 seconds
  time cargo build --release
  echo

  popd
}

binary-sizes() {
  local oils=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  ninja $oils
  # stripped: 2.4 MB
  ls -l --si $oils

  pushd ../../shells/brush
  strip -o target/release/brush.stripped target/release/brush
  # stripped: 7.3 MB
  ls -l --si target/release
  popd

  pushd ../../shells/rusty_bash
  strip -o target/release/sush.stripped target/release/sush
  # stripped: 3.4 MB
  ls -l --si target/release
  echo
  popd
}

symbols() {
  pushd ../../shells/brush
  #file target/release/brush

  echo 'BRUSH'
  # 6140
  nm target/release/brush | wc -l
  popd

  pushd ../../shells/rusty_bash
  # Not stripped
  #file target/release/sush

  echo 'SUSH'
  # 10380
  nm target/release/sush | wc -l
  # More symbols
  # nm target/debug/sush | wc -l
  popd

  #local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp
  local dbg=_bin/cxx-dbg/bin/oils_for_unix.mycpp
  ninja $osh 

  echo 'OSH'
  # 9810 - lots of string literals?
  nm $osh | wc -l
  #nm $osh | less

  #ninja $dbg
  # 17570
  #nm $dbg | wc -l
}

install-geiger() {
  # https://github.com/geiger-rs/cargo-geiger
  . ~/.cargo/env

  # 2:34 minutes
  cargo install --locked cargo-geiger
}

# This is DESTRUCTIVE
geiger-report() {
  if true; then
    pushd ../../shells/brush

    . ~/.cargo/env

    # doesn't work
    #time cargo geiger --workspace
    #time cargo geiger --package brush-core --package brush-parser

    popd
  fi

  if false; then
    pushd ../../shells/rusty_bash

    . ~/.cargo/env

    # this cleans the build
    #
    # Functions  Expressions  Impls   Traits  Methods
    # 181/1056   9377/45040   114/158 30/32   463/2887
    #
    # x/y
    # x = unsafe used by build
    # y = unsafe in crate

    # ~7 seconds
    time cargo geiger 

    popd
  fi
}

#
# Spec Tests
#

run-file() {
  local spec_name=${1:-smoke}
  shift  # Pass list of shells

  local spec_subdir='spec-any'
  local base_dir=_tmp/spec/$spec_subdir
  mkdir -v -p $base_dir
  
  # spec/tilde hangs under toysh - need timeout
  sh-spec spec/$spec_name.test.sh \
    --tsv-output $base_dir/${spec_name}.result.tsv \
    --timeout 1 \
    "$@" \
    "${SHELLS[@]}"
}

osh-all() {
  # Like test/spec.sh {osh,ysh}-all, but it compares against different binaries

  # For debugging hangs
  #export MAX_PROCS=1

  ninja $OSH_TARGET

  test/spec-runner.sh shell-sanity-check "${SHELLS[@]}"

  local spec_subdir=spec-any

  local status
  set +o errexit
  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    osh spec-any $spec_subdir "$@"
  status=$?
  set -o errexit

  # Write comparison even if we failed
  write-compare-html $spec_subdir

  return $status
}

#
# HTML
#

summary-tsv-row() {
  ### Print one row or the last total row

  local spec_subdir=$1
  shift

  if test $# -eq 1; then
    local spec_name=$1
    local -a tsv_files=( _tmp/spec/$spec_subdir/$spec_name.result.tsv )
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

  if (sh == "bash") {
    bash[result] += 1
  } else if (sh == "mksh") {
    mksh[result] += 1
  } else if (sh == "ksh") {
    ksh[result] += 1
  } else if (sh == "toysh") {
    toysh[result] += 1
  } else if (sh == "sush") {
    sush[result] += 1
  } else if (sh == "brush") {
    brush[result] += 1
  } else if (sh == "osh") {
    osh[result] += 1
  }
}

END { 
  if (spec_name == "TOTAL") {
    href = ""
  } else {
    href = sprintf("%s.html", spec_name)
  }
  bash_total = ("pass" in bash) ? bash["pass"] : 0
  ksh_total = ("pass" in ksh) ? ksh["pass"] : 0
  mksh_total = ("pass" in mksh) ? mksh["pass"] : 0
  toysh_total = ("pass" in toysh) ? toysh["pass"] : 0
  sush_total = ("pass" in sush) ? sush["pass"] : 0
  brush_total = ("pass" in brush) ? brush["pass"] : 0
  osh_total = ("pass" in osh) ? osh["pass"] : 0

  # TODO: change this color
  row_css_class = "cpp-good"  # green

  row = sprintf("%s %s %s %d %d %d %d %d %d %d",
         row_css_class,
         spec_name, href,
         bash_total,
         ksh_total,
         mksh_total,
         toysh_total,
         sush_total,
         brush_total,
         osh_total)

  # Turn tabs into spaces - awk mutates the row!
  gsub(/ /, "\t", row)
  print row
}
' "${tsv_files[@]}"
}

summary-tsv() {
  local spec_subdir=$1

  local manifest=_tmp/spec/SUITE-osh.txt

  # Can't go at the top level because files might not exist!
  tsv-row \
    'ROW_CSS_CLASS' 'name' 'name_HREF' "${SH_LABELS[@]}"

  # total row rows goes at the TOP, so it's in <thead> and not sorted.
  summary-tsv-row $spec_subdir _tmp/spec/$spec_subdir/*.result.tsv

  head -n $NUM_SPEC_TASKS $manifest | sort |
  while read spec_name; do
    summary-tsv-row $spec_subdir $spec_name
  done 
}

html-summary-header() {
  local prefix=../../..
  spec-html-head $prefix 'Compatibility Report'

  table-sort-begin "width50"

  echo '
<p id="home-link">
  <!-- The release index is two dirs up -->
  <a href="../..">Up</a> |
  <a href="/">oils.pub</a>
</p>

<h1>Compatibility Report</h1>

<p>Here is the total number of passing tests.  TODO: we should also verify
tests that do not pass.
</p>

<p>Another view: <a href="index.html">index.html</a>.
</p>
'
}

html-summary-footer() {
  echo '
<p>Generated by <code>test/spec-any.sh</code>.
</p>

<p><a href="SUMMARY.tsv">Raw TSV</a>
</p>
'
  table-sort-end 'SUMMARY'  # The table name
}

write-compare-html() {
  local spec_subdir=$1

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
bash            integer
mksh            integer
ksh             integer
toysh           integer
sush            integer
brush           integer
osh             integer
EOF

  { html-summary-header
    # total row isn't sorted
    tsv2html --thead-offset 1 $dir/SUMMARY.tsv
    html-summary-footer
  } > $out

  log "Comparison: file://$REPO_ROOT/$out"
}


# Metrics to put in summary.csv
#
# - for each shell, total passing (possibly biased by what we mark PASS)
# - for each shell, the number of tests it passes that bash (4 or 5) also passes (unbiased)
#   - this avoids being biased by spec/errexit-osh, spec/strict-options
#
# Columns: bash mksh ksh toysh sush brush
# Other columns:
# - bash minus $SH, for each
# - osh minus $SH, for each
#
# compatibility.html   "Which new shell is the most compatible?"
#                       With totals of every spec test file, and percentage summaries
#   passing.html       # per file, sortable -
#   delta-bash.html    # ...
#   delta-osh.html
# Later:
#   majority.html      # if non-zero status, does STDOUT match majority?
#                      # this is a more NEUTRAL metric, but requires a TSV file
#                      from sh_spec.py with stdout
#
# Maybe produce versus-bash.csv, versus-osh.csv

list() {
  mkdir -p _tmp/spec  # _all-parallel also does this
  test/spec-runner.sh write-suite-manifests
  wc -l _tmp/spec/SUITE-*

  # TODO:
  # - Remove zsh test files?
  # - What about *-bash test cases?  These aren't clearly organized

  cat _tmp/spec/SUITE-osh.txt
}

readonly ERRORS=(
  'echo )'  # parse error
  'cd -z'   # usage error
  'cd /zzz'   # runtime error
)

survey-errors() {
  set +o errexit
  for sh in "${SHELLS[@]}"; do
    echo
    echo " === $sh"
    for code in "${ERRORS[@]}"; do
      $sh -c "$code"
    done
  done
}

task-five "$@"
