#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

source $REPO_ROOT/build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

boilerplate() {
  local rel_name=${1:-osh/bool_stat}
  local ns=$(basename $rel_name)  # bool_stat

  local name="$(echo $rel_name | tr / _)"

  local prefix="cpp/$name"  # cpp/core_bool_stat
  echo $prefix

  local guard="$(echo $rel_name | tr a-z/ A-Z_)_H"
  echo $guard

  cat > $prefix.h <<EOF
// $name.h

#ifndef $guard
#define $guard

namespace $ns {
 
}  // namespace $ns

#endif  // $guard

EOF

  cat > $prefix.cc <<EOF
// $name.cc

#include "$name.h"

namespace $ns {

// TODO: fill in

}  // namespace $ns
EOF

  ls -l $prefix.{h,cc}
  echo Wrote $prefix.{h,cc}


}

# Copied greatest.h into cpp/ afterward
download() {
  wget --directory _deps \
    https://github.com/silentbicycle/greatest/archive/v1.4.2.tar.gz
}

CPPFLAGS="$CXXFLAGS -O0 -g -fsanitize=address"
export ASAN_OPTIONS='detect_leaks=0'  # like build/mycpp.sh

# Copied from mycpp/run.sh
cpp-compile() {
  local main_cc=$1
  local bin=$2
  shift 2

  mkdir -p _bin
  $CXX -o $bin $CPPFLAGS -I . $main_cc "$@" -lstdc++
}

cpp-compile-run() {
  local main_cc=$1
  shift

  local name=$(basename $main_cc .cc)
  local bin=_bin/$name

  cpp-compile $main_cc $bin "$@"
  $bin
}

heap() {
  cpp-compile-run demo/heap.cc "$@"
}

"$@"
