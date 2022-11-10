#!/usr/bin/env bash
#
# Usage:
#   devtools/R-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

show-r() {
  set -x
  which R
  R --version
  set +x
}

test-r-packages() {
  # tidyr and stringr don't print anything
  R_LIBS_USER=$R_PATH Rscript -e 'library(dplyr); library(tidyr); library(stringr); print("OK")'
}

soil-run() {
  show-r
  echo

  test-r-packages
  echo

  benchmarks/report.sh report-test
  echo
}

"$@"
