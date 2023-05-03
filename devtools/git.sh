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

merge-to-staging() {
  local do_push=${1:-T}  # pass F to disable

  local branch=$(git rev-parse --abbrev-ref HEAD)

  if test "$do_push" = T; then
    git checkout soil-staging &&
    git merge $branch &&
    git push &&
    git checkout $branch
  else
    git checkout soil-staging &&
    git merge $branch &&
    git checkout $branch
  fi
}

fetch-staging-and-master() {
  git fetch origin soil-staging:soil-staging master:master
}

# https://stackoverflow.com/questions/11021287/git-detect-if-there-are-untracked-files-quickly

untracked() {
  local count
  git ls-files --other --directory --exclude-standard
}

error-if-untracked() {
  local count
  count=$(untracked | tee _tmp/untracked | wc -l)
  if test $count -ne 0; then
    echo 'Clean up untracked files first:'
    echo

    cat _tmp/untracked
    return 1
  fi

  echo 'OK: no untracked files'
  return 0
}

"$@"
