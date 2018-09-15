#!/bin/bash
#
# Usage:
#   ./complete.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

git-audit() {
  local file=testdata/completion/git-completion.bash

  echo
  echo --
  # Search for completion builtin usage
  grep -E -w --color 'complete|compgen|compopt' $file

  echo
  echo --
  # Search for special complation var usage
  grep -E --color 'COMP_[A-Z]+' $file

  echo
  echo --
  # Search for array usage
  grep -E --color ']=' $file
  grep -E --color ']+=' $file
}

"$@"
