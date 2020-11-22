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
# https://man.sr.ht/builds.sr.ht/compatibility.md
#
# Basically, it supports up to 4 files called .builds/*.yml.
# And we need to upload an SSH key as secret via the web UI.

keygen() {
  ssh-keygen -t rsa -b 4096 -C "andyc sr.ht" -f rsa_srht
}

#
# Run remotely
#

publish-html-assuming-ssh-key() {
  if true; then
    deploy-job-results 'srht-' JOB_ID JOB_URL
  else
    deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  write-jobs-raw 'srht-'

  remote-rewrite-jobs-index 'srht-'

  # note: we could speed jobs up by doing this separately?
  remote-cleanup-jobs-index 'srht-'

  # toil-worker.sh recorded this for us
  local status
  status=$(cat _tmp/toil/exit-status.txt)

  log "Exiting with saved status $status"

  return $status
}

#
# For create-cache.yml
#

compress-deps() {
  ### Compress output of tarball-deps and spec-deps
  echo TODO
}

"$@"
