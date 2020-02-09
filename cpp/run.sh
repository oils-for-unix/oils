#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

"$@"
