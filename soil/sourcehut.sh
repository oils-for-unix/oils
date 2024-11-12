#!/usr/bin/env bash
#
# Usage:
#   soil/sourcehut.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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
  local job_name=$1

  if true; then
    soil/web-worker.sh deploy-job-results 'sourcehut-' $JOB_ID $job_name JOB_ID JOB_URL
  else
    soil/web-worker.sh deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  local commit_hash
  # written by save-metadata in soil/worker.sh
  commit_hash=$(cat _tmp/soil/commit-hash.txt)

  # Note: the directory structure will be overlapping, unlike Github which has
  # GITHUB_RUN_NUMBER
  #
  # sourcehut-jobs/
  #   1234/foo.wwz  # individual jobs
  #   1235/bar.wwz
  #   git-0101abab/index.html  # commit hash

  time soil/web-worker.sh remote-event-job-done 'sourcehut-' "git-$commit_hash"
}

#
# For create-cache.yml
#

compress-dir() {
  local dir=$1

  local out_dir=_tmp/deps-cache
  mkdir -p $out_dir

  local name=$(basename $dir)

  local out=$out_dir/$name.tar.xz 

  log "Compressing $dir -> $out"

  tar --create --xz --file $out $dir
  ls -l $out
}

compress-deps() {
  ### Compress output of tarball-deps and spec-deps

  compress-dir _deps/cpython-full
  compress-dir _deps/re2c-1.0.3
  compress-dir _deps/cmark-0.29.0

  compress-dir _deps/spec-bin
}

"$@"
