#!/bin/bash
#
# Usage:
#   ./git.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# To run pull requests on my machine.
#
# From
# https://help.github.com/en/articles/checking-out-pull-requests-locally

pull-pr() {
  local pr_id=$1
   git fetch origin pull/$pr_id/head:pr/$pr_id
}

"$@"
