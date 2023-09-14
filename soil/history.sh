#!/usr/bin/env bash
#
# Analyze history
#
# Usage:
#   soil/history.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)

#source $REPO_ROOT/soil/common.sh


readonly BASE_DIR=_tmp/soil-history

readonly HOST=travis-ci.oilshell.org

list() {
  ### Used the sync'd testdata
  local dir=${1:-_tmp/github-jobs}

  # 4 digits
  ssh travis-ci.oilshell.org 'ls travis-ci.oilshell.org/github-jobs/'
}

find-wwz() {
  ### Used the sync'd testdata
  local dir=${1:-_tmp/github-jobs}

  mkdir -p $BASE_DIR

  # 4 digits
  ssh $HOST \
    'cd travis-ci.oilshell.org && find github-jobs/48?? -name benchmarks2.wwz' \
    | tee $BASE_DIR/listing.txt
}

sync() {
  local dir=$HOST
  rsync \
    --archive --verbose \
    --files-from $BASE_DIR/listing.txt \
    $HOST:$dir/ $BASE_DIR/
}

list-zip() {
  unzip -l $BASE_DIR/github-jobs/5000/*.wwz
}

extract-one() {
  local id=$1
  local dir=$BASE_DIR/github-jobs/$id
  pushd $dir

  # commit-hash.txt
  unzip benchmarks2.wwz '_tmp/gc-cachegrind/stage2/*' '_tmp/soil/*' || true
  popd
}

extract-all() {
  for dir in $BASE_DIR/github-jobs/48??; do
    local id=$(basename $dir)
    extract-one $id
  done
}

show-all() {
  #local pat='mut+alloc+free+gc'
  local pat='bumpleak'

  grep "$pat" \
    $BASE_DIR/github-jobs/????/_tmp/gc-cachegrind/stage2/ex.compute-fib.tsv
}

"$@"
