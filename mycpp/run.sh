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

source $THIS_DIR/common.sh  # MYPY_REPO

#
# Utilities
#

gen-ctags() {
  ctags -R $MYPY_REPO
}

"$@"
