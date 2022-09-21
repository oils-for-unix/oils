#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source soil/web-remote.sh
source test/common.sh

test-format-wwz-index() {
  soil/worker.sh JOB-dummy

  local out=_tmp/format-wwz-index.html

  format-wwz-index DUMMY_JOB_ID > $out
  echo "Wrote $out"
}

test-make-job-wwz() {
  make-job-wwz dummy

  # Makes it in the root dir
  ls -l *.wwz
  unzip -l dummy.wwz
}

test-image-stats() {
  # NOTE: can't run sudo automatically
  sudo soil/host-shim.sh save-image-stats

  format-image-stats '' '../../web' > _tmp/soil/image.html

  # Problem: absolute JS and CSS links don't work here.
  ls -l _tmp/soil/image.html
}

all() {
  run-test-funcs
}

"$@"
