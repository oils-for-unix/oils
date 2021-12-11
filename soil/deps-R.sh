#!/usr/bin/env bash
#
# Usage:
#   ./deps-R.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

other-tests() {
  readonly R_PATH=~/R  # duplicates what's in test/common.sh

  # Install to a directory that doesn't require root.  This requires setting
  # R_LIBS_USER.  Or library(dplyr, lib.loc = "~/R", but the former is preferable.
  mkdir -p ~/R

  # Note: dplyr 1.0.3 as of January 2021 made these fail on Xenial.  See R 4.0
  # installation below.
  INSTALL_DEST=$R_PATH Rscript -e 'install.packages(c("dplyr", "tidyr", "stringr"), lib=Sys.getenv("INSTALL_DEST"), repos="https://cloud.r-project.org")'
}

"$@"
