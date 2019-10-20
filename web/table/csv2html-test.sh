#!/usr/bin/env bash
#
# Usage:
#   ./csv2html-test.sh <function name>

. ~/hg/taste/taste.sh

set -o nounset
set -o pipefail
set -o errexit

test-no-schema() {
  cat >_tmp/foo.csv <<EOF
a_number,b
1,2
3,4
NA,4
EOF

  ./csv2html.py _tmp/foo.csv
}

test-schema() {
  cat >_tmp/bar.csv <<EOF
name,name_HREF,num
spam,#spam,11
eggs,#eggs,22
ham,#ham,99
xxx,#xxx,123456
zzz,#zzz,NA
EOF

  # NOTE: Columns are out of order, which is OK.

  # type: could be html-anchor:shell-id, html-href:shell-id

  cat >_tmp/bar.schema.csv <<EOF
column_name,type
num,integer
name,string
name_HREF,string
EOF

  ./csv2html.py _tmp/bar.csv
}

test-precision() {
  cat >_tmp/prec.csv <<EOF
name,age
andy,1.2345
bob,2.3456789
EOF

  # NOTE: Columns are out of order, which is OK.

  # type: could be html-anchor:shell-id, html-href:shell-id

  cat >_tmp/prec.schema.csv <<EOF
column_name,type,precision
name,string,1
age,double,3
EOF

  ./csv2html.py _tmp/prec.csv
}


if test $# -eq 0; then
  test-no-schema
  echo '--'
  test-schema
  echo '--'
  test-precision
else
  "$@"
fi


