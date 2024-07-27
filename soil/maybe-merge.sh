#!/usr/bin/env bash
#
# Fast forward a green branch to master.
#
# Usage:
#   soil/maybe-merge.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh

fast-forward()  {
  # Generate a token in "Settings" -> Developer Settings
  # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
  # Should be a secret in Github Actions
  local github_token=$1

  local commit_hash=${2:-}
  local to_branch=${3:-'master'}

  # local testing
  if test -z "$github_token"; then
    # set by YAML
    github_token=${OILS_GITHUB_KEY:-}

    # Local testing
    if test -z "$github_token"; then
      github_token=$(cat token.txt)
    fi
  fi
  if test -z "$commit_hash"; then 
    # $GITHUB_SHA is the commit, set by Github Actions
    commit_hash=${GITHUB_SHA:-}

    # Local testing
    if test -z "$commit_hash"; then 
      commit_hash='ae02c9d6e8ba8e19399de556292a1d93faa220d3'
    fi
  fi

  # Adapted from
  # https://stackoverflow.com/questions/55800253/how-can-i-do-a-fast-forward-merge-using-the-github-api
  #
  # https://docs.github.com/en/rest/git/refs#update-a-reference

  local response=_tmp/soil/gh-fast-forward.json

  echo
  echo "Trying to fast-forward branch $to_branch to commit $commit_hash"
  echo

  curl \
    -o $response \
    -X PATCH \
    -H "Content-Type: application/json" \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Authorization: token ${github_token}" \
    https://api.github.com/repos/oils-for-unix/oils/git/refs/heads/$to_branch \
    -d '{"sha": "'$commit_hash'", "force": false }'
    
  local error
  error=$(cat $response | jq '.message')

  local ret
  if test "$error" = 'null'; then
    echo "Success:"
    ret=0
  else
    echo 'ERROR fast forwarding:'
    ret=1
  fi

  cat $response
  return $ret
}

test-fast-forward()  {
  fast-forward '' '' dev-andy-3
}

all-status-zero() {
  ### Do all files contain status 0?

  for path in "$@"; do
    # There may be a newline on the end, which 'read' stops at.
    read -r status unused_job_id < $path

    if test "$status" != '0'; then
      echo "$path = $status"
      return 1
    fi
  done

  return 0
}

soil-run() {
  local github_token=${1:-}  # OILS_GITHUB_KEY
  local run_id=${2:-}  # $GITHUB_RUN_ID
  local commit_hash=${3:-}  # GITHUB_SHA
  local to_branch=${4:-}  # defaults to master

  if test -z "$run_id"; then
    # GITHUB_RUN_ID is set by Github Actions
    run_id=${GITHUB_RUN_ID:-}

    # local testing
    if test -z "$run_id"; then
      run_id='2526880241'
    fi
  fi

  local branch=$(git rev-parse --abbrev-ref HEAD)
  echo "Should we auto-merge branch $branch to master?"

  if test "$branch" != 'soil-staging'; then
    echo 'No, only soil-staging is merged to master'
    return
  fi

  local dir=_tmp/status-api
  rm -f -v $dir/*
  mkdir -p $dir

  # These tiny files are written by each Soil task
  local url_base="http://$SOIL_HOST/status-api/github/$run_id"

  #local jobs='dummy pea other-tests'  # minimal set of jobs to wait for
  local jobs=$(soil/worker.sh list-jobs)

  local -a args=()
  for job in $jobs; do  # relies on word splitting

    # output each URL in a different file
    args=( "${args[@]}" -o $dir/$job $url_base/$job )
  done

  curl -v ${args[@]}

  if all-status-zero $dir/*; then
    fast-forward "$github_token" "$commit_hash" "$to_branch"
  fi
}

test-soil-run() {
  # test with non-master branch
  # other params have testing defaults
  soil-run '' '' '' '' dev-andy-3
}

"$@"
