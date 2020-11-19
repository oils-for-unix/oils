#!/usr/bin/env bash
#
# Usage:
#   ./sourcehut.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Reuse some stuff
source services/travis.sh

# Relevant docs:
#
# https://man.sr.ht/tutorials/getting-started-with-builds.md
# https://man.sr.ht/builds.sr.ht/#secrets
#
# Basically, it supports up to 4 files called .builds/*.yml.
# And we need to upload an SSH key as secret via the web UI.

keygen() {
  ssh-keygen -t rsa -b 4096 -C "andyc sr.ht" -f rsa_srht
}

#
# Run remotely
#

deploy-job-results() {
  local job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  make-job-wwz $job_id

  # Written by toil-worker.sh
  # TODO:
  # - Don't export these, just pass to env_to_json
  # - if it exists, publish _tmp/spec/*.stats.txt and publish it?
  #   - osh failures and total failures
  export TASK_RUN_START_TIME=$(cat _tmp/toil/task-run-start-time.txt)
  export TASK_DEPLOY_START_TIME=$(date +%s)

  services/env_to_json.py \
    JOB_ID \
    JOB_URL \
    > $job_id.json

  # So we don't have to unzip it
  cp _tmp/toil/INDEX.tsv $job_id.tsv

  # Copy wwz, tsv, json
  scp-results 'srht-' $job_id.*

  log ''
  log "http://travis-ci.oilshell.org/srht-jobs/"
  log "http://travis-ci.oilshell.org/srht-jobs/$job_id.wwz/"
  log ''
}


publish-html-assuming-ssh-key() {
  if true; then
    deploy-job-results
  else
    deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  write-jobs-raw 'srht-'

  remote-rewrite-jobs-index 'srht-'

  # note: we could speed jobs up by doing this separately?
  remote-cleanup-jobs-index 'srht-'

  # toil-worker.sh recorded this for us
  return $(cat _tmp/toil/exit-status.txt)
}


"$@"
