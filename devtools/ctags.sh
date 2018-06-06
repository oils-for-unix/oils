#!/bin/bash
#
# Usage:
#   ./ctags.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

ubuntu-deps() {
  sudo apt install exuberant-ctags
}

# Creates a 9 MB file.
index-python() {
  pushd Python-2.7.13/
  ctags --recurse
  ls -l tags
  popd
}

"$@"
