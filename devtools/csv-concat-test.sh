#!/bin/bash
#
# Usage:
#   ./csv-concat-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # fail

test-good() {
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

  ./csv_concat.py _tmp/test{1,2}.csv

  cat >_tmp/bad.csv <<EOF
name,age,another
dave,30,oops
EOF

  ./csv_concat.py _tmp/test{1,2}.csv _tmp/bad.csv
  if test $? -eq 1; then
    echo 'Expected failure OK'
  else
    fail 'Should have failed'
  fi
}

travis() {
  cd devtools
  test-good
}

"$@"
