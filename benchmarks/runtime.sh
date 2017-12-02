#!/bin/bash
#
# Usage:
#   ./runtime.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# NOTE: Same list in oilshell.org/blob/run.sh.
files() {
  cat <<EOF
tcc-0.9.26.tar.bz2
yash-2.46.tar.xz
ocaml-4.06.0.tar.xz
uftrace-0.8.1.tar.gz
EOF
}

readonly TAR_DIR=_tmp/benchmarks/runtime 
readonly OSH=$PWD/bin/osh

download() {
  files | xargs -n 1 -I {} --verbose -- \
    wget --directory $TAR_DIR 'https://oilshell.org/blob/testdata/{}'
}

extract() {
  time for f in $TAR_DIR/*z; do
    tar -x --directory $TAR_DIR --file $f 
  done
  ls -l $TAR_DIR
}

# TODO: Run under bash and osh.  Look for all the files that changed?  Using
# 'find'?  And then diff them.

yash() {
  pushd $TAR_DIR/yash-2.46
  $OSH ./configure
  popd
}

"$@"
