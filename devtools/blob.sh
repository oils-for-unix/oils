#!/usr/bin/env bash
#
# Manage the old oilshell.org/blob/ dir
# Created after Dreamhost disabled oilshell.org
#
# Usage:
#   devtools/blob.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/blob

download() {
  mkdir -p $BASE_DIR
  time rsync --archive --verbose chubot@travis-ci.oilshell.org:oilshell.org/blob/ $BASE_DIR/
}

upload-op() {
  #ssh op.oils.pub 'ls'
  ssh op.oils.pub 'mkdir -v -p op.oils.pub/blob; ls op.oils.pub/blob'
  time rsync --archive --verbose $BASE_DIR/ op.oils.pub:op.oils.pub/blob/
}

upload-mb() {
  #ssh mb.oils.pub 'ls www'
  ssh mb.oils.pub 'mkdir -v -p www/mb.oils.pub/blob; ls www/mb.oils.pub/blob'
  time rsync --archive --verbose $BASE_DIR/ mb.oils.pub:www/mb.oils.pub/blob/
}

"$@"
