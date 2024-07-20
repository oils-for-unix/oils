#!/usr/bin/env bash
#
# Usage:
#   test/tsv-lib-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source test/tsv-lib.sh

test-concat-rows() {
  local status

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

  nq-run status \
    tsv-concat _tmp/test{1,2}.csv
  nq-assert 0 = "$status"

  cat >_tmp/bad.csv <<EOF
name,age,another
dave,30,oops
EOF

  nq-run status \
    tsv-concat _tmp/test{1,2}.csv _tmp/bad.csv
  nq-assert 1 = "$status"
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

test-tsv2html() {
  cat >_tmp/test2.tsv <<EOF
name
carol
EOF

  tsv2html _tmp/test2.tsv

  # This test passes on my desktop, but 'other-tests' Soil image doesn't have
  # python3 yet.
  #tsv2html3 _tmp/test2.tsv
}

soil-run() {
  devtools/byo.sh test $0
}

task-five "$@"
