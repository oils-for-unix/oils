#!/usr/bin/env bash
#
# Usage:
#   devtools/tsv-lib-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh
source test/common.sh  # fail

test-concat-rows() {
  set +o errexit

  mkdir -p _tmp
  cat >_tmp/test1.csv <<EOF
name,age
alice,0
bob,10
EOF

  cat >_tmp/test2.csv <<EOF
name,age
carol,20
EOF

  tsv-concat _tmp/test{1,2}.csv

  cat >_tmp/bad.csv <<EOF
name,age,another
dave,30,oops
EOF

  tsv-concat _tmp/test{1,2}.csv _tmp/bad.csv
  if test $? -eq 1; then
    echo 'Expected failure OK'
  else
    fail 'Should have failed'
  fi
}

test-add-const-column() {
  here-schema-tsv >_tmp/add.tsv <<EOF
name  age
alice 10
bob   20
EOF
  cat _tmp/add.tsv

  tsv-add-const-column host_name $(hostname) < _tmp/add.tsv
}

soil-run() {
  run-test-funcs
}

"$@"
