#!/usr/bin/env bash
#
# Misc automation.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..

source build/dev-shell.sh

#
# Utilities
#

gen-ctags() {
  ctags -R $TODO_MYPY_REPO
}

"$@"
