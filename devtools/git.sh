#!/usr/bin/env bash
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

log-staging() {
  ### log: for working with the merge bot
  git log soil-staging..
}

diff-staging() {
  ### diff: for working with the merge bot
  git diff soil-staging..
}

rebase-staging() {
  git rebase -i soil-staging
}

"$@"
