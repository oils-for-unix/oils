#!/usr/bin/env bash
#
# Usage:
#   soil/github-actions.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

keygen() {
  # rsa_github_actions is private, and sent to Github to log into the server
  # rsa_github_actions.pub is public, and put in authorized_keys on the server
  ssh-keygen -t rsa -b 4096 -C "oilshell github-actions" -f rsa_github_actions
}

#
# Run remotely
#

publish-html-assuming-ssh-key() {
  local job_name=$1
  local update_status_api=${2:-}

  if true; then
    # https://docs.github.com/en/actions/reference/environment-variables

    # Recommended by the docs
    export JOB_URL="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"

    soil/web-worker.sh deploy-job-results 'github-' $GITHUB_RUN_NUMBER $job_name \
      JOB_URL \
      GITHUB_WORKFLOW	\
      GITHUB_RUN_ID \
      GITHUB_RUN_NUMBER \
      GITHUB_JOB \
      GITHUB_ACTION \
      GITHUB_REF \
      GITHUB_PR_NUMBER \
      GITHUB_PR_HEAD_REF \
      GITHUB_PR_HEAD_SHA
  else
    soil/web-worker.sh deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  # Calls rewrite-jobs-index and cleanup-jobs-index
  time soil/web-worker.sh remote-event-job-done 'github-' $GITHUB_RUN_NUMBER

  if test -n "$update_status_api"; then
    soil/web-worker.sh scp-status-api "$GITHUB_RUN_ID" "$job_name"
    soil/web-worker.sh remote-cleanup-status-api
  fi
}

# Notes on Github secrets:

# - "Secrets are environment variables that are encrypted. Anyone with
#    collaborator access to this repository can use these secrets for Actions."
#
# - "Secrets are not passed to workflows that are triggered by a pull request from a fork"
#
# TODO: We're not following the principle of least privilege!  Really we should
# have an "append-only" capability?  So then pull requests from untrusted forks
# can trigger builds?
#
# Instead of SSH, we should use curl to POST a .zip file to PHP script on
# travis-ci.oilshell.org?

load-secret-key() {
  local privkey=/tmp/rsa_github_actions

  if test -n "${TOIL_KEY:-}"; then
    echo "$TOIL_KEY" > $privkey
  else
    echo '$TOIL_KEY not set'
    exit 1
  fi

  chmod 600 $privkey
  eval "$(ssh-agent -s)"
  ssh-add $privkey
}


# Overwrites the function in soil/travis.sh
publish-html() {
  ### Publish job HTML, and optionally status-api

  load-secret-key

  set -x
  # $1 can be the job name
  publish-html-assuming-ssh-key "$@"
}

publish-cpp-tarball() {
  load-secret-key

  soil/web-worker.sh publish-cpp-tarball github-
}

# Don't need this because Github Actions has it pre-installed.
install-podman() {
  sudo apt-get install -y podman
  podman --version
}

run-job() {
  ### Called by YAML config

  # Unlike sourcehut, Github Actions runs one job per machine.  So we fix the
  # mount permissions and run the job in one step.

  local job_name=$1
  local docker=${2:-docker}

  # I think it starts in the repo
  # cd $REPO_ROOT

  soil/host-shim.sh mount-perms $REPO_ROOT
  echo
  echo

  soil/host-shim.sh run-job-uke $docker $REPO_ROOT $job_name
}

publish-and-exit() {
  ### Called by YAML config
  local job_name=$1
  # second param is passed to publish-html

  # Unlike sourcehut, Github Actions runs one job per machine.  So we publish
  # HTML and exit in one step.

  publish-html "$@"

  soil/host-shim.sh did-all-succeed $job_name
}

"$@"
