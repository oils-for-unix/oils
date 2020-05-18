#!/bin/bash
#
# Usage:
#   ./csv2html-test.sh <function name>

source  ~/hg/taste/taste.sh

set -o nounset
set -o pipefail
set -o errexit

readonly REPO_ROOT=$(readlink -f $(dirname $0))/../..

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
  cat <<EOF
<body onload="initPage(gUrlHash, gTableStates, kStatusElem);"
      onhashchange="onHashChange(gUrlHash, gTableStates, kStatusElem);">
  <p id="status"></p>

EOF
}

footer() {
  local name=$1

  cat <<EOF

    <!-- page globals -->
    <script type="text/javascript">
      var gUrlHash = new UrlHash(location.hash);
      var gTableStates = {};
      var kStatusElem = document.getElementById('status');

      function initPage(urlHash, tableStates, statusElem) {
        var elem = document.getElementById('$name');
        makeTablesSortable(urlHash, [elem], tableStates);
        updateTables(urlHash, tableStates, statusElem);
      }

      function onHashChange(urlHash, tableStates, statusElem) {
        updateTables(urlHash, tableStates, statusElem);
      }
    </script>

  </body>
</html>
EOF
}

write-html() {
  local name=$1
  local out=$BASE_DIR/$name.html

  { header
    ./csv2html.py _tmp/$name.csv 
    footer $name
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

  write-html prec
}


if test $# -eq 0; then
  link-static

  test-no-schema
  echo '--'
  test-schema
  echo '--'
  test-precision
else
  "$@"
fi


