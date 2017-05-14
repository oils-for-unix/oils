#!/bin/bash
#
# Usage:
#   ./declare.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  readonly __ONE=bar  # declare -r
  export readonly __TWO=bar  # declare -x
  export readonly local __THREE=bar  # declare -x
  readonly __FOUR=bar
  export __FOUR  # declare -rx
                 # OK export readonly doesn't work!  That was silly.
                 # not sure why I thought they can be combined.

  # Show everything
  declare -p  | grep __
}

demo-clean() {
  # Show a clean demo
  env -i $0 demo
}

"$@"
