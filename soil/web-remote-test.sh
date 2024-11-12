#!/usr/bin/env bash

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh
source $LIB_OSH/no-quotes.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

# Problem: this includes test-collect-json
# (which uses python3)
source soil/web-worker.sh  # make-job-wwz

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

ROOT-test-image-stats() {
  # NOTE: can't run sudo automatically
  sudo soil/host-shim.sh save-image-stats

  format-image-stats '' '../../web' > _tmp/soil/image.html

  # Problem: absolute JS and CSS links don't work here.
  ls -l _tmp/soil/image.html
}

soil-run() {
  devtools/byo.sh test $0
  #run-test-funcs
}

task-five "$@"
