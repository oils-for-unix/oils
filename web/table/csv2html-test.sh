#!/usr/bin/env bash
#
# Usage:
#   ./csv2html-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly REPO_ROOT=$(readlink -f $(dirname $0))/../..

source $REPO_ROOT/test/common.sh
source $REPO_ROOT/web/table/html.sh


readonly BASE_DIR=_tmp/www

link-static() {
  mkdir -p $BASE_DIR

  ln -s -f -v \
    $PWD/../ajax.js \
    $PWD/table-sort.js \
    $PWD/table-sort.css \
    $BASE_DIR
}

html-head() {
  PYTHONPATH=$REPO_ROOT $REPO_ROOT/doctools/html_head.py "$@"
}

header() {
  html-head --title 'csv2html-test' \
    ajax.js table-sort.js table-sort.css

  table-sort-begin
}

write-html() {
  local name=$1
  shift

  local out=$BASE_DIR/$name.html

  { header
    ./csv2html.py "$@" _tmp/$name.csv 
    table-sort-end $name
  } > $out
  echo "Wrote $out"
}

test-no-schema() {
  cat >_tmp/foo.csv <<EOF
a_number,b
1,2
3,4
NA,4
EOF

  write-html foo
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

  write-html bar

  cp _tmp/bar.csv _tmp/bar2.csv
  cp _tmp/bar.schema.csv _tmp/bar2.schema.csv
  write-html bar2 --thead-offset 1
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
age,double,2
EOF

  write-html prec
}

test-timestamp() {
  cat >_tmp/timestamp.csv <<EOF
name,start_time,end_time
python3,0.1,1000000000.2
bash,1100000000.3,1200000000.4
EOF

  # NOTE: Columns are out of order, which is OK.

  # type: could be html-anchor:shell-id, html-href:shell-id

  cat >_tmp/timestamp.schema.csv <<EOF
column_name,type,strftime
name,string,-
start_time,float,iso
end_time,float,iso
EOF

  write-html timestamp

  cp _tmp/timestamp.csv _tmp/timestamp2.csv

  cat >_tmp/timestamp2.schema.csv <<EOF
column_name,type,strftime
name,string,-
start_time,float,iso
end_time,float,%H:%M:%S
EOF

  write-html timestamp2
}

test-row-css-class() {
  cat >_tmp/css.csv <<EOF
name,age
andy,1.2345
bob,2.3456789
EOF

  # NOTE: Columns are out of order, which is OK.

  # type: could be html-anchor:shell-id, html-href:shell-id

  cat >_tmp/css.schema.csv <<EOF
column_name,type,precision
name,string,1
age,double,3
EOF

  write-html css --css-class-pattern 'myclass ^a'

  cat >_tmp/css2.csv <<EOF
ROW_CSS_CLASS,name,age
pass,andy,1.2345
fail,bob,2.3456789
EOF

  # NOTE: Columns are out of order, which is OK.

  # type: could be html-anchor:shell-id, html-href:shell-id

  cat >_tmp/css2.schema.csv <<EOF
column_name,type,precision
ROW_CSS_CLASS,string,0
name,string,1
age,double,3
EOF

  write-html css2

}

all() {
  link-static
  echo
  run-test-funcs
}

"$@"

