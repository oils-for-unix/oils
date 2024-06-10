#!/usr/bin/env bash
#
# Build binaries for the spec tests.  This is necessary because they tickle
# behavior in minor versions of each shell.
#
# Usage:
#   test/spec-bin.sh <function name>
#
# Instructions:
#   test/spec-bin.sh download     # Get the right version of every tarball
#   test/spec-bin.sh extract-all  # Extract source
#   test/spec-bin.sh build-all    # Compile
#   test/spec-bin.sh copy-all     # Put them in ../oil_DEPS/spec-bin
#   test/spec-bin.sh test-all     # Run a small smoke test
#
# Once you've run all steps manually and understand how they work, run them
# all at once with:
#
#   test/spec-bin.sh all-steps

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source devtools/run-task.sh
#source test/spec-common.sh

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

run-task "$@"
