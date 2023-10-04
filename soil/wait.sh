#!/usr/bin/env bash
#
# Wait for artifacts on a web server.
#
# Usage:
#   soil/wait.sh

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source soil/common.sh

curl-until-200() {
  ### Retry fetch until HTTP 200, REUSING curl process AND connection

  # Similar to
  # https://stackoverflow.com/questions/42873285/curl-retry-mechanism

  local url=$1
  local output_dir=$2
  local num_retries=${3:-10}  # number of times through the loop
  local interval=${4:-10}  # retry every n seconds

  # --retry-all-errors and --fail are used to make curl try on a 404

  # Note: might need --retry-conn-refused as well, in case the server
  # disconnects

  curl \
    --verbose \
    --remote-name \
    --output-dir $output_dir \
    --max-time 10 \
    --retry $num_retries \
    --retry-all-errors \
    --fail \
    --retry-delay $interval \
    $url
}

http-wait() {
  local url=$1
  local sleep_secs=${2:-1}  # don't bother trying until this amount of time

  while test $(curl); do
    echo
  done
}

# Users
# - test/wild.sh soil-run
# - benchmarks/perf.sh in the raw-vm task
# - test/ble.sh, in app-tests task

for-cpp-tarball()  {
  local prefix=${1:-github-}

  # Wait 3 minutes for cpp-tarball task, before starting to hit the server
  local sleep_secs=${2:-180}

  # Retry for 12 times, every 10 seconds = 2 minutes.

  # If we have 10 clients, then we're hitting it once a second, which is not
  # unreasonable.  We're also keeping 10 connections

  local num_retries=${3:-12}
  local interval=${4:-10}

  local git_commit_dir
  git_commit_dir=$(git-commit-dir $prefix)

  local url="$git_commit_dir/oils-for-unix.tar"

  set -x
  sleep $sleep_secs

  curl-until-200 $url _release/ $num_retries $interval
}

readonly TEST_FILE='oilshell.org/tmp/curl-test'

for-test-file() {
  curl-until-200 "http://www.$TEST_FILE" _tmp/ 5 10
}

touch-remote() {
  ssh oilshell.org "echo hi > $TEST_FILE"
}

rm-remote() {
  ssh oilshell.org "rm -v $TEST_FILE"
}

test-for-cpp-tarball()  {
  for-cpp-tarball
}

"$@"
