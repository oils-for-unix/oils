#!/usr/bin/env bash
#
# Usage:
#   build/dev-setup-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

smoke-test() {
  ### For the fast possible development experience

  # To put python2 WEDGE in $PATH
  source build/dev-shell.sh

  bin/osh -c 'echo HI osh python $OILS_VERSION'
  bin/ysh -c 'echo HI ysh python $OILS_VERSION'

  # ASAN doesn't work with musl libc on Alpine
  # https://gitlab.alpinelinux.org/alpine/aports/-/issues/10304

  ninja _bin/cxx-dbg/{osh,ysh}

  _bin/cxx-dbg/osh -c 'echo HI osh C++ $OILS_VERSION'
  _bin/cxx-dbg/ysh -c 'echo HI ysh C++ $OILS_VERSION'
}

"$@"
