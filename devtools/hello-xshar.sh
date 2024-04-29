#!/usr/bin/env bash
#
# Test file
#
# Usage:
#   devtools/hello-xshar.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  echo "args $@"

  echo 'hello-xshar.sh: listing files'
  echo

  find yaks/ -type f

  echo
  echo 'hello-xshar.sh: done'
}

"$@"
