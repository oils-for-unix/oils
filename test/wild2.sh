#!/bin/bash
#
# Wild tests that actually run code.
#
# TODO:
# - Use a better name.
# - There are a lot of hard-coded paths in this script.
#
# Usage:
#   ./wild2.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

replace-shebang() {
  local dir=$1
  find $dir -name '*.sh' \
    | xargs -- sed -i 's|^#!/bin/bash|#!/home/andy/git/oil/bin/osh|'
}

readonly TOYBOX_DIR=~/git/other/toybox

replace-toybox() {
  replace-shebang $TOYBOX_DIR
}

build-toybox() {
  cd $TOYBOX_DIR
  make clean
  make
}

readonly DE_DIR=~/git/basis-build/_tmp/debootstrap

bash-debootstrap() {
  DEBOOTSTRAP_DIR=$DE_DIR $DE_DIR/debootstrap "$@"
}

osh-debootstrap() {
  DEBOOTSTRAP_DIR=$DE_DIR bin/osh $DE_DIR/debootstrap "$@"
}

de-help() {
  osh-debootstrap --help
}

# Probably not great to run as root.
de-xenial() {
  local sh=$1
  local target_dir=_tmp/debootstrap/$sh-xenial
  mkdir -p $target_dir
  time sudo $0 ${sh}-debootstrap xenial $target_dir || true
}

bash-de-xenial() {
  de-xenial bash
}

# Probably not great to run as root.
osh-de-xenial() {
  de-xenial osh
}

readonly PYTHON_DIR=~/src/Python-2.7.9

py-configure() {
  cd $PYTHON_DIR
  # Hm this seems to take a long time to parse.  TODO: Show parse timing with
  # -v or xtrace or something.

  # TODO: Implement ':'.  It's a special builtin.
  time ~/git/oil/bin/osh configure
}


"$@"
