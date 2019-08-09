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

# Copied from metrics/bytecode.sh, build/cpython-defs.sh, etc.
py-files() {
  awk ' $1 ~ /\.py$/ { print $1 }' _build/oil/opy-app-deps.txt
}

oil-ctags-out() {

  # Vim complains unless we have this
  echo $'!_TAG_FILE_SORTED\t0'

  # We want an explicit manifest to avoid walking _chroot/ and so forth.  ctags
  # --exclude doesn't work well.

  py-files | ctags --filter | sort 
}

index-oil-py() {
  oil-ctags-out > tags
}

"$@"
