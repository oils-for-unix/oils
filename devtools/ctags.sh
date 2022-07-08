#!/usr/bin/env bash
#
# Function to generate tags files, e.g. for Vim Ctrl-] lookup.
#
# Usage:
#   devtools/ctags.sh <function name>

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

oil-ctags-out() {

  # Vim complains unless we have this
  echo $'!_TAG_FILE_SORTED\t0'

  # We want an explicit manifest to avoid walking _chroot/ and so forth.  ctags
  # --exclude doesn't work well.

  test/lint.sh find-src-files | ctags --filter | sort 
}

index-oil() {
  time oil-ctags-out > tags
  ls -l tags
}

"$@"
