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
  time for f in $TAR_DIR/*.{xz,bz2}; do
    tar -x --directory $TAR_DIR --file $f 
  done
  ls -l $TAR_DIR
}

configure-and-show-new() {
  local dir=$1

  pushd $dir >/dev/null
  touch __TIMESTAMP
  #$OSH -x ./configure
  $OSH ./configure

  echo
  echo "--- NEW FILES ---"
  echo

  find . -type f -newer __TIMESTAMP
  popd >/dev/null
}

# TODO: Run under bash and osh.  Look for all the files that changed?  Using
# 'find'?  And then diff them.

yash() {
  configure-and-show-new $TAR_DIR/yash-2.46
}

# test expression problem
tcc() {
  configure-and-show-new $TAR_DIR/tcc-0.9.26
}

# What is the s:?
uftrace() {
  configure-and-show-new $TAR_DIR/uftrace-0.8.1
}

ocaml() {
  configure-and-show-new $TAR_DIR/ocaml-4.06.0
}

# Same problem as tcc
qemu-old() {
  configure-and-show-new ~/src/qemu-1.6.0
}

"$@"
