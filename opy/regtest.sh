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

# NOTE: This doesn't work on Ubuntu 17.10 because it uses Python 2.7.14, and I
# generated the golden file on Ubuntu 16.04 with Python 2.7.12.  (Although I
# verified it on two different machines with Python 2.7.12.)  I'm not going to
# worry about it for now because I think it's due to marshal / hashing
# differences, and OPy will eventually not use marshal, and probably not
# hashing either.
#
# See comments in 'build.sh compile-manifest'.

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

# For debugging golden differences.  We want it to be the same on multiple
# machines.
compare-other-machine() {
  local rel_path=${1:-'opy/compiler2/transformer.pyc'}
  # TODO: Copy zip from flanders?
  local zip=_tmp/flanders/bytecode-opy.zip 

  ls -l _tmp/regtest/$rel_path

  unzip -p $rel_path $zip | od -c
}

smoke-three-modes() {
  compile oil
  $THIS_DIR/../bin/opyc eval '1+2*3'
  echo '4+5*6' | $THIS_DIR/../bin/opyc repl
}

"$@"
