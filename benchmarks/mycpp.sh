#!/usr/bin/env bash
#
# Analyze how mycpp speeds up programs.
#
# Usage:
#   benchmarks/mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source benchmarks/common.sh
source test/common.sh  # R_PATH
source test/tsv-lib.sh  # tsv2html

print-report() {
  local in_dir=$1

  benchmark-html-head 'mycpp Code Generation'

  cat <<EOF
  <body class="width60">
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
EOF
  cmark <<EOF

## mycpp Code Generation

Measure the speedup from mycpp, and the resource usage.

Source code: [oil/mycpp/examples](https://github.com/oilshell/oil/tree/master/mycpp/examples)

EOF

  cmark <<EOF
### User Time (milliseconds)

Lower ratios are better.

EOF

  tsv2html $in_dir/user_time.tsv

  cmark <<EOF
  ### Max Resident Set Size (MB)

Lower ratios are better.  We use MB (powers of 10), not MiB (powers of 2).

EOF

  tsv2html $in_dir/max_rss.tsv


if false; then
  cmark <<EOF
### Details

EOF

  tsv2html $in_dir/details.tsv
fi

  cmark <<'EOF'
### TODO

- Benchmark with both GCC and Clang, and show compiler provenance.  Right now
  the compiler is forced to be the system `c++`.
- Run this benchmark on multiple machines.

EOF

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  # Run AND report benchmarks.

  local base_dir=${1:-_tmp/mycpp-examples}
  local in_tsv=_test/benchmark-table.tsv

  # Force SERIAL reexecution
  # TODO: This is why benchmarks don't really belong in Ninja?
  rm -r -f --verbose _test/tasks/benchmark/

  ninja -j 1 $in_tsv

  mkdir -p $base_dir/raw
  cp -v $in_tsv $base_dir/raw

  local dir2=$base_dir/stage2
  mkdir -p $dir2

  R_LIBS_USER=$R_PATH benchmarks/report.R mycpp $base_dir/raw $dir2

  benchmarks/report.sh stage3 $base_dir mycpp
}

"$@"
