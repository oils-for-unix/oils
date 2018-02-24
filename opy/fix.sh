#!/bin/bash
#
# Usage:
#   ./fix.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# -w to write it back
print() {
  2to3 --fix print "$@"
}

"$@"
