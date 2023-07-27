#!/usr/bin/env bash
#
# Run yapf formatter; it's installed in ~/wedge/ by build/deps.sh
#
# Usage:
#   test/format.sh <function name>

. build/dev-shell.sh  # python3 in $PATH

yapf-version() {
  python3 -m yapf --version
}

# For now, run yapf on specific files.  TODO: could query git for the files
# that are are different from master branch, and run it on those.
yapf-files() {
  python3 -m yapf -i "$@"
}

"$@"
