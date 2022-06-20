#!/usr/bin/env bash
#
# Usage:
#   ./maybe-merge.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

soil-run() {
  echo 'Hello from maybe-merge.sh'

  local branch=$(git rev-parse --abbrev-ref HEAD)
  echo "BRANCH = $branch"

  if test "$branch" = 'soil-staging'; then
    echo 'TODO: check all state'
  fi
}

"$@"
