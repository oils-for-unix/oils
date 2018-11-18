#!/bin/bash
#
# Usage:
#   ./html.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

basic-head() {
  local title=$1
  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>$title</title>
    <style>
      body {
        margin: 0 auto;
        width: 40em;
      }
      #home-link {
        text-align: right;
      }
    </style>
  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h3>$title</h3>
    <p>
EOF
}

basic-tail() {
  cat <<EOF
  </body>
</html>
EOF
}

"$@"
