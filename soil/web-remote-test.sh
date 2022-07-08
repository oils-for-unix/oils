#!/usr/bin/env bash

source soil/web-remote.sh
source test/common.sh

set -o nounset
set -o pipefail
set -o errexit

test-format-wwz-index() {
  soil/worker.sh JOB-dummy
  format-wwz-index DUMMY_JOB_ID
}

all() {
  run-test-funcs
}

"$@"
