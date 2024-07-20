#!/usr/bin/env bash
#
# Take stable measurements of GC
#
# Usage:
#   benchmarks/gc-cachegrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source benchmarks/common.sh
source build/dev-shell.sh  # $R_LIBS_USER
source test/tsv-lib.sh

readonly BASE_DIR=_tmp/gc-cachegrind

print-report() {
  local in_dir=$1

  benchmark-html-head 'Memory Management (stable measurements)'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF

  cmark << 'EOF'
## Memory Management (stable measurements)

Source code: [oil/benchmarks/gc-cachegrind.sh](https://github.com/oilshell/oil/tree/master/benchmarks/gc-cachegrind.sh)
EOF

  cmark <<'EOF'
#### parse.abuild

EOF

  tsv2html $in_dir/parse.abuild.tsv

  cmark <<'EOF'
#### ex.compute-fib

EOF

  tsv2html $in_dir/ex.compute-fib.tsv


  cat <<EOF

  </body>
</html>
EOF
}

make-report() {
  mkdir -p $BASE_DIR/{stage1,stage2}

  # Concatenate tiny files
  benchmarks/cachegrind_to_tsv.py $BASE_DIR/raw/cachegrind-*.txt \
    > $BASE_DIR/stage1/cachegrind.tsv

  #pretty-tsv $BASE_DIR/stage1/cachegrind.tsv

  # Make TSV files
  benchmarks/report.R gc-cachegrind $BASE_DIR $BASE_DIR/stage2

  #pretty-tsv $BASE_DIR/stage2/counts.tsv

  # Make HTML
  benchmarks/report.sh stage3 $BASE_DIR
}

soil-run() {
  ### Run in soil/benchmarks2 (stable timings)

  benchmarks/gc.sh measure-cachegrind

  make-report
}

"$@"
