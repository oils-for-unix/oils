#!/usr/bin/env bash
#
# Manual tool to go with soil/maybe-merge.sh.
#
# Usage:
#   devtools/github.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# A github commit status that's required for the master branch.
# This is a reminder to change PR targets to soil-staging, NOT master.

# SETUP:
#    github.com/oilshell/oil 
# -> Settings tab
# -> Branches on LHS
# -> Add Branch Protection Rule 'master'
# -> Require Status Checks To Pass Before Merging
# -> soil/allow-emergency-push-to-master

allow-emergency-push-to-master() {

  local commit_hash=${1:-0187d24d84a1f14a96eeb3a57bf7920787082ea9}
  local github_token
  github_token=$(cat token.txt)

  curl \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: token $github_token" \
    "https://api.github.com/repos/oilshell/oil/statuses/$commit_hash" \
    -d '
{ "state": "success",
  "target_url": "https://travis-ci.oilshell.org",
  "description": "Usually you should merge to soil-staging, NOT master",
  "context": "soil/allow-emergency-push-to-master"
}'

}

"$@"
