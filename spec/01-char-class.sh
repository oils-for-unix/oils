#!/bin/bash
#
# Usage:
#   ./01-char-class.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  [[ a == [a] ]]
  [[ a != [^a] ]]

  [[ a == [ab] ]]
  [[ a != [^ab] ]]

  [[ a == [[:alpha:]] ]]
  [[ a != [^[:alpha:]] ]]
  [[ 0 == [^[:alpha:]] ]]

  # NOTE: there is only one negation.  You can't mix them.
  [[ 0 == [^[:alpha:]] ]]

  echo
  echo 'ALL PASSED'
}

"$@"
