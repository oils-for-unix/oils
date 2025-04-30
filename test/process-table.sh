#!/usr/bin/env bash
#
# Process table tests for job control.
#
# Usage:
#   test/process-table.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)"/..; pwd)

source benchmarks/common.sh  # html-head
source build/dev-shell.sh  # python2
source test/common.sh
source test/tsv-lib.sh  # time-tsv

readonly BASE_DIR=_tmp/process-table

readonly OSH_CPP=_bin/cxx-dbg/osh
readonly -a JC_SHELLS=(bash dash mksh zsh bin/osh $OSH_CPP)

print-tasks() {
  readonly -a SNIPPETS=(
    fgproc bgproc
    fgpipe fgpipe-lastpipe 
    bgpipe bgpipe-lastpipe
    subshell csub psub
  )

  for sh in "${JC_SHELLS[@]}"; do
    for snippet in "${SNIPPETS[@]}"; do
      for interactive in - yes; do
        echo "${sh}${TAB}${snippet}${TAB}${interactive}"
      done
    done
  done
}

run-tasks() {
  local tsv_out=$1 

  while read sh snippet interactive; do
    # Suppress failure, since exit code is recorded
    time-tsv -o $tsv_out --append \
      --field $sh --field $snippet --field $interactive -- \
      test/process-table-portable.sh run_snippet $sh $snippet $interactive || true
  done
}

report-html-head() {
  local title=$1

  local base_url='../../web'

  html-head --title "$title" \
    "$base_url/table/table-sort.js" \
    "$base_url/table/table-sort.css" \
    "$base_url/base.css"
}

print-report() {
  local tsv_out=$1

  local title='Process State for Job Control'
  report-html-head "$title"

  # Extra style, doesn't go on any element
  # Pink background same as web/spec-tests.css
  echo '<style> .fail { background-color: #ffe0e0 } </style>'

  # Copied from uftrace
  echo '<body style="margin: 0 auto; width: 40em; font-size: large">'

  echo "<h1>$title</h1>"

  tsv2html $tsv_out 

  echo '
  </body>
</html>
'
}

add-css-class() {
  python2 -c '
import sys
for i, line in enumerate(sys.stdin):
  rest = line.rstrip()
  if i == 0:
    print("ROW_CSS_CLASS\t%s" % rest)
  else:
    row_css_class = "pass" if line.startswith("0") else "fail"
    print("%s\t%s" % (row_css_class, rest))
'
}

make-report() {
  local times_tsv=$1

  # TODO: Add ROW_CSS_CLASS when status != 0
  add-css-class < $times_tsv > $BASE_DIR/index.tsv

  local html=$BASE_DIR/index.html

  print-report $BASE_DIR/index.tsv > $html

  echo "Wrote $html"
}

soil-run() {
  test/process-table-portable.sh setup

  ninja $OSH_CPP

  local times_tsv=$BASE_DIR/times.tsv
  mkdir -p $BASE_DIR

  # note: it seems better to align everything right

  here-schema-tsv >$BASE_DIR/index.schema.tsv <<EOF
column_name   type
ROW_CSS_CLASS string
status        integer
elapsed_secs  number
sh            string
snippet       string
interactive   string
EOF

  time-tsv -o $times_tsv --print-header \
    --field sh --field snippet --field interactive

  print-tasks | run-tasks $times_tsv

  make-report $times_tsv
}

run-for-release() {
  # Same thing as CI -- put output in _tmp/process-table/index.html
  soil-run
}

#
# Reproduce bugs
#

timeout-issue() {
  ### For some reason bgproc-interactive conflicts with 'timeout' command

  set -x

  # doesn't hang with OSH
  timeout 900 $0 test-bgproc-interactive

  # doesn't hang
  SH=dash timeout --foreground 900 $0 test-bgproc-interactive
  SH=bash timeout --foreground 900 $0 test-bgproc-interactive

  # these both hang
  # SH=dash timeout 900 $0 test-bgproc-interactive
  # SH=bash timeout 900 $0 test-bgproc-interactive
}

time-tsv-issue() {
  #time-tsv -o _tmp/tsv -- $0 test-bgproc-interactive
  time-tsv -o _tmp/tsv -- $0 soil-run
}

"$@"
