#!/usr/bin/env bash
#
# Analyze how mycpp speeds up programs.
#
# Usage:
#   benchmarks/mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source benchmarks/common.sh

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

  cat <<EOF
  </body>
</html>
EOF
}


"$@"
