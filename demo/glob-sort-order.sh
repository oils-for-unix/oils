#!/usr/bin/env bash
#
# Usage:
#   ./glob-sort-order.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  local dir=_tmp/glob-sort-order
  mkdir -p $dir
  cd $dir


  echo LANG=${LANG:-}
  echo LC_ALL=${LC_ALL:-}
  echo LC_COLLATE=${LC_COLLATE:-}

  touch ':' '_' '{}' '&' '<'

  # default
  echo *

  export LC_COLLATE=C 
  echo *

  export LC_ALL=C
  echo *

  # same as above
  export LC_ALL=C.UTF-8
  echo *

  export LC_COLLATE=en_US.UTF_8
  echo *

  # Hm the united states one is different!
  export LC_ALL=en_US.UTF_8
  echo *
}

"$@"
