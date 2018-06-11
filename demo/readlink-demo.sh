#!/bin/bash
#
# Usage:
#   ./readlink-demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

two-file-symlinks() {
  # NOTE: Two levels of symlinks requires readlink -f, not readlink.
  ln -s -f $PWD/demo/readlink-demo-target.sh /tmp/demo.sh
  ln -s -f /tmp/demo.sh /tmp/demo-level2.sh
  /tmp/demo-level2.sh
}

dir-symlink() {
  ln -s -f --no-target-directory $PWD/demo/ /tmp/oil-demo
  /tmp/oil-demo/readlink-demo-target.sh
}

all() {
  echo 'Two files:'
  two-file-symlinks
  echo

  echo 'Dirs:'
  dir-symlink
  echo
}

"$@"
