#!/usr/bin/env bash
#
# Usage:
#   test/spec-bin.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

#
# "Non-hermetic"
#

link-busybox-ash() {
  ### Non-hermetic ash only used for benchmarks / Soil dev-minimal

  # Could delete this at some point
  mkdir -p _tmp/shells
  ln -s -f --verbose "$(which busybox)" _tmp/shells/ash
}

# dash and bash should be there by default on Ubuntu.
install-shells-with-apt() {
  ### Non-hermetic shells; test/spec-bin.sh replaces this for most purposes

  set -x  # show what needs sudo

  # pass -y to install in an automated way
  sudo apt "$@" install busybox-static mksh zsh
  set +x
  link-busybox-ash
}

bash-upstream() {
  wget --directory _tmp --no-clobber \
    https://ftp.gnu.org/gnu/bash/bash-5.2.21.tar.gz
}

task-five "$@"
