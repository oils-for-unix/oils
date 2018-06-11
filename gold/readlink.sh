#!/bin/bash
#
# Usage:
#   ./readlink.sh <function name>

set -o nounset
set -o pipefail
#set -o errexit

dir-does-not-exist() {
  readlink -f /nonexistent
  echo $?

  readlink -f /nonexistent/foo
  echo $?
}

"$@"
