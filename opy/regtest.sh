#!/bin/bash
#
# Usage:
#   ./regtest.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
source $THIS_DIR/common.sh

readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

# Everything we care about compiling:
_all-py-files() {
  local fmt=$1

  # Python files (including build scripts and unit tests, which aren't in the
  # binary).
  oil-python-sources $REPO_ROOT "$fmt"

  # - stdlib deps of bin.oil and bin.opy_
  # NOTE: These end with .pyc
  cat \
    $REPO_ROOT/_build/py-to-compile.txt \
    $REPO_ROOT/_build/{oil,opy}/py-to-compile.txt
}

# Only compile unique
all-py-files() {
  _all-py-files "$@" | sort | uniq
}

_copy() {
  local dest_dir=$1
  local src_path=$2
  local dest_rel_path=$3

  local dest=$dest_dir/$dest_rel_path

  dest=${dest%c}  # .pyc -> py

  mkdir -p $(dirname $dest)
  cp -v --no-target-directory $src_path $dest
}

import() {
  local dest=_regtest/src
  mkdir -p $dest

  all-py-files '%p %P\n' | xargs -n 2 -- $0 _copy $dest
}

#
# Now compiled the files imported
#

manifest() {
  # add .pyc at the end
  find _regtest/src -type f -a -printf '%p %Pc\n'
}

# 19 seconds on lisa.  This should be a benchmark.

# TODO: Parallelize with xargs.  compile-manifest in build.sh is serial.  Just
# needs a mkdir.

compile() {
  local pat=${1:-}
  local dest=_tmp/regtest
  mkdir -p $dest
  time manifest | egrep "$pat" | ./build.sh compile-manifest $dest
}

checksum() {
  find _tmp/regtest -type f | xargs $THIS_DIR/../bin/opyc dis-md5 | sort -n
}

verify-golden() {
  if checksum | diff -u _regtest/dis-md5.golden.txt -; then
    echo OK
  else
    return 1
  fi
}

lines() {
  find _regtest/src -type f | xargs wc -l | sort -n
}

compare-one() {
  local rel_path='opy/compiler2/transformer.pyc'

  ls -l _tmp/regtest/$rel_path

  # TODO: Copy zip from flanders?
  unzip -p $rel_path _tmp/flanders/bytecode-opy.zip | od -c
}

smoke-three-modes() {
  compile oil
  $THIS_DIR/../bin/opyc eval '1+2*3'
  echo '4+5*6' | $THIS_DIR/../bin/opyc repl
}

"$@"
