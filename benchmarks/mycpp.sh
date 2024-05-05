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
source build/dev-shell.sh  # R_LIBS_USER
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

  cmark <<EOF
### System Time (milliseconds)

Lower ratios are better.

EOF

  tsv2html $in_dir/sys_time.tsv

  cmark << 'EOF'
---
[raw benchmark files](raw/benchmark/-wwz-index)

EOF


if false; then
  cmark <<EOF
### Details

EOF

  tsv2html $in_dir/details.tsv
fi

  cat <<EOF
  </body>
</html>
EOF
}

soil-run() {
  # Run and report mycpp/examples BENCHMARKS only.

  local base_dir=${1:-_tmp/mycpp-examples}
  local in_tsv=_test/benchmark-table.tsv

  # Force SERIAL reexecution of benchmarks
  # Notes:
  # - This is why benchmarks don't really belong in Ninja?
  # - mycpp/TEST.sh test-translator does 'mycpp-logs-equal', which also runs
  #   tests

  local task_dir=_test/tasks/benchmark
  rm -r -f --verbose $task_dir
  ninja -j 1 $in_tsv

  mkdir -p $base_dir/raw
  cp -v $in_tsv $base_dir/raw
  cp -R $task_dir/ $base_dir/raw/benchmark/

  local dir2=$base_dir/stage2
  mkdir -p $dir2

  benchmarks/report.R mycpp $base_dir/raw $dir2

  benchmarks/report.sh stage3 $base_dir mycpp
}

"$@"
