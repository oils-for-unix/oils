#!/usr/bin/env bash
#
# Usage:
#   soil/tests.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh

# TODO:
# - Use a proper test framework.
# - Put this into soil/other-tests too!

all() {
  echo TODO
}

"$@"
