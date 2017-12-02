#!/bin/bash
#
# Test scripts found in the wild for both correctness and performance.
#
# Usage:
#   ./runtime.sh <function name>
#
# TODO:
# - Merge this with test/wild2.sh?  benchmarks/wild3.sh or test/wild3.sh?
# - abuild -h -- time it

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

readonly TAR_DIR=$PWD/_tmp/benchmarks/runtime 
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

configure-and-copy() {
  local src_dir=$1
  local sh=$2
  local out_dir=$3

  mkdir -p $out_dir

  # These hand-written configure scripts must be run from their own directory,
  # unlike autoconf's scripts.

  pushd $src_dir >/dev/null
  touch __TIMESTAMP
  #$OSH -x ./configure
  $sh ./configure

  echo
  echo "--- NEW FILES ---"
  echo

  find . -type f -newer __TIMESTAMP | xargs -I {} --verbose -- cp {} $out_dir
  popd >/dev/null
}

configure-twice() {
  local dir=$1
  local label=$(basename $dir)
  configure-and-copy $dir bash $TAR_DIR/${label}__bash
  configure-and-copy $dir dash $TAR_DIR/${label}__dash
  configure-and-copy $dir $OSH $TAR_DIR/${label}__osh
}

yash() {
  configure-twice $TAR_DIR/yash-2.46
}

# Works for bash/dash/osh!
tcc() {
  configure-twice $TAR_DIR/tcc-0.9.26
  #configure-and-show-new $TAR_DIR/tcc-0.9.26
}

# Works for bash/dash/osh!
uftrace() {
  configure-twice $TAR_DIR/uftrace-0.8.1
  #configure-and-show-new $TAR_DIR/uftrace-0.8.1
}

# Works for bash/dash/osh!
ocaml() {
  configure-twice $TAR_DIR/ocaml-4.06.0
  #mkdir -p _tmp/ocaml
  #configure-and-copy $TAR_DIR/ocaml-4.06.0 $OSH $PWD/_tmp/ocaml
}

# Same problem as tcc
qemu-old() {
  local out_dir=$PWD/_tmp/qemu-old
  mkdir -p $out_dir
  configure-and-copy ~/src/qemu-1.6.0 $OSH $out_dir
}

"$@"
