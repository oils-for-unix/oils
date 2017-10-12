#!/bin/bash
#
# Test for csv_to_html.py.
#
# Usage:
#   ./csv-to-html-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

test-basic() {
  ./csv_to_html.py <<EOF
a_number,b
1,2
3,4
NA,4
EOF
}

test-col-format() {
  ./csv_to_html.py \
    --col-format 'b <a href="../{b}/metric.html">{b}</a>' <<EOF
a,b
1,2015-05-01
3,2015-05-02
EOF
}

test-var-def() {
  ./csv_to_html.py \
    --def 'v VALUE' \
    --col-format 'b <a href="../{b}/metric.html">{v}</a>' <<EOF
a,b
1,2
3,4
EOF
}

test-as-percent() {
  ./csv_to_html.py \
    --as-percent b <<EOF
a,b
A,0.21
B,0.001
C,0.0009
D,0.0001
EOF
}

if test $# -eq 0; then
  test-basic
  echo '--'
  test-col-format
  echo '--'
  test-var-def
  echo '--'
  test-as-percent
  echo '--'
  echo 'OK'
else
  "$@"
fi
