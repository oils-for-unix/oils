#!/usr/bin/env bash
#
# Automation for Travis CI.
#
# Usage:
#   soil/travis.sh <function name>
#
# This contains setup for travis-ci.oilshell.org (the server), as well as the
# client, which is an ephemeral machine for each Travis run.
#
# The server needs a public key and the client needs a private key.
#
# Other TODO:
#
# And I probably need a cron job on my own domain to administer oilshell.org
# - wwz log files
#   - backup (does sync_logs.sh do this?)
#   - cleanup
# - clean up old travis CI build logs
# - back up /downloads/ dir
#
# Related docs:
#
# https://docs.travis-ci.com/user/environment-variables/#defining-encrypted-variables-in-travisyml

# https://oncletom.io/2016/travis-ssh-deploy/
# https://github.com/dwyl/learn-travis/blob/master/encrypted-ssh-keys-deployment.md

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh
source soil/web-worker.sh

#
# Key Generation: One Time Setup
#

# Need to pass --pre because I hit this bug.  Does not inspire confidence.
# https://github.com/travis-ci/travis.rb/issues/711

deps() {
  # travis gem needed to encrypt ssh private key (also adds to .travis.yml)
  sudo gem install travis --pre  # --version '1.8.10'
}

keygen() {
  local comment=${1:-travis-ci.oilshell}
  local file=${2:-rsa_travis}
  ssh-keygen -t rsa -b 4096 -C "$comment" -f $file
}

encrypt-private-key() {
  ### Use travis gem to add an encrypted version to .travis.yml

  # 'travis login' first

  #travis encrypt-file ./rsa_travis --add
  travis encrypt-file ./rsa_travis soil/rsa_travis.enc --add
}

deploy-public-key() {
  # note: permissions must be 700
  ssh travis_admin@travis-ci.oilshell.org mkdir -v -p .ssh

  # TODO: or append it?
  scp rsa_travis.pub travis_admin@travis-ci.oilshell.org:.ssh/authorized_keys
}

decrypt-key() {
  local out=$1
  openssl aes-256-cbc \
    -K $encrypted_a65247dffca0_key -iv $encrypted_a65247dffca0_iv \
    -in soil/rsa_travis.enc -out $out -d
}

publish-html-assuming-ssh-key() {
  if true; then
    deploy-job-results 'travis-' \
      TRAVIS_JOB_NAME \
      TRAVIS_OS_NAME \
      TRAVIS_TIMER_START_TIME \
      TRAVIS_BUILD_WEB_URL \
      TRAVIS_JOB_WEB_URL \
      TRAVIS_BUILD_NUMBER \
      TRAVIS_JOB_NUMBER \
      TRAVIS_BRANCH \
      TRAVIS_COMMIT \
      TRAVIS_COMMIT_MESSAGE
  else
    deploy-test-wwz  # dummy data that doesn't depend on the build
  fi

  write-jobs-raw 'travis-'
  remote-rewrite-jobs-index 'travis-'

  # note: we could speed jobs up by doing this separately?
  remote-cleanup-jobs-index 'travis-'

  # soil/worker.sh recorded this for us
  return $(cat _tmp/soil/exit-status.txt)
}

publish-html() {
  local privkey=/tmp/rsa_travis

  decrypt-key $privkey
  chmod 600 $privkey
  eval "$(ssh-agent -s)"
  ssh-add $privkey

  publish-html-assuming-ssh-key
}

#
# Maintenance
#

# Sometimes the cache gets stale and you have to delete it.  Weird.
delete-caches() {
  travis cache -d
}

if test $(basename $0) = 'travis.sh'; then
  "$@"
fi
