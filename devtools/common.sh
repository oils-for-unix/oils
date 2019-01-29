#!/bin/bash
# 
# Common shell functions for the devtools directory.
#
# Usage:
#   source devtools/common.sh

html-footer() {
  cat <<EOF
    </table>
  </body>
</html>
EOF
}

# Copied from test/unit.sh
banner() {
  echo -----
  echo "$@"
  echo -----
}

