#!/usr/bin/env bash
#
# Usage:
#   devtools/R-test.sh <function name>

source test/common.sh  # R_PATH

show-r() {
  set -x
  which R
  R --version
  set +x
}

test-r-packages() {
  R_LIBS_USER=$R_PATH Rscript -e 'library(dplyr)'
}

soil-task() {
  show-r
  test-r-packages
}

"$@"
