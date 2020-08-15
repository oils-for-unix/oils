#!/bin/bash
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

EOF

  cmark <<EOF
### TODO

- what does this test?
EOF

  tsv2html $in_dir/details.tsv

  cat <<EOF
  </body>
</html>
EOF
}


"$@"
