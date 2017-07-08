#!/usr/bin/env bash
#
# Usage:
#   ./errexit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

succeed() {   
  return 0
}

fail() {   
  return 1
}

main() {
  succeed && echo "OK 1"
  fail && echo "OK 2"  # Swallos the error because of errexit, not good!
  succeed && echo "OK 3"
}

"$@"
