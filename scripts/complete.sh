#!/bin/bash
#
# Usage:
#   ./complete.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

git-audit() {
  grep -E -w 'complete|compgen|compopt' testdata/completion/git-completion.bash
}

"$@"
