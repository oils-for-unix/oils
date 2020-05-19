#!/bin/bash
#
# Usage:
#   ./html.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

table-sort-begin() {
  local body_css_class=${1:-}

  cat <<EOF

<body class="$body_css_class"
      onload="initPage(gUrlHash, gTableStates, kStatusElem);"
      onhashchange="onHashChange(gUrlHash, gTableStates, kStatusElem);">
  <p id="status"></p>

EOF
}

table-sort-end() {
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
