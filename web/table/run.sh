#!/usr/bin/env bash
#
# Usage:
#   ./table.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly WWW=_tmp/www
readonly CSV=_tmp/table.csv

link-static() {
  ln -s -f -v \
    $PWD/../ajax.js \
    $PWD/table-sort.js \
    $PWD/table-sort.css \
    $WWW
}

_html-header() {
  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>table-sort.js Example</title>

    <!-- for ajaxGet, UrlHash, etc. -->
    <script type="text/javascript" src="ajax.js"></script>
    <link rel="stylesheet" type="text/css" href="table-sort.css" />
    <script type="text/javascript" src="table-sort.js"></script>
  </head>

  <body onload="initPage(gUrlHash, gTableStates, kStatusElem);"
        onhashchange="onHashChange(gUrlHash, gTableStates, kStatusElem);">
    <p id="status"></p>

    <table id="mytable">
      <colgroup>
        <col type="number" />
        <col type="case-insensitive" />
      </colgroup>
EOF
}

# NOTE: There is no initial sort?
_html-footer() {
  cat <<EOF
      <tfoot>
        <tr>
          <td>Footer 1</td>
          <td>Footer 2</td>
        </tr>
      </tfoot>
    </table>

    <!-- page globals -->
    <script type="text/javascript">
      var gUrlHash = new UrlHash(location.hash);
      var gTableStates = {};
      var kStatusElem = document.getElementById('status');

      function initPage(urlHash, tableStates, statusElem) {
        var elem = document.getElementById('mytable');
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

write-csv() {
  cat >$CSV <<EOF
metric,fraction
A,0.21
B,0.001
C,0.0009
D,0.0001
-,0.1
F,-
EOF
}

print-table() {
  _html-header

  ./csv_to_html.py \
    --col-format 'metric <a href="metric.html#metric={metric}">{metric}</a>' \
    --as-percent fraction \
    < $CSV

  _html-footer
}

write-table() {
  mkdir -p $WWW

  link-static

  write-csv

  local out=$WWW/table-example.html
  print-table >$out

  ls -l $out
}

"$@"
