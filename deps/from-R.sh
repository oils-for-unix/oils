#!/usr/bin/env bash
#
# Install CRAN packages.
#
# Usage:
#   deps/from-R.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: cache the package downloads with Docker, since they takes about 20
# seconds to retrieve.


# Notes: dplyr 1.0.3 as of January 2021 made these fail on Xenial.  
# I did an R 4.0 installation.  See build/py.sh install-new-R
#
# February 2023: compile errors with dplyr and Ubuntu 18.04, which has R 3.4.4.
# tidyverse has minimum R of 3.6.
# I need to install a new R again.

other-tests() {
  readonly R_PATH=~/R  # duplicates what's in test/common.sh

  # Install to a directory that doesn't require root.  This requires setting
  # R_LIBS_USER.  Or library(dplyr, lib.loc = "~/R", but the former is preferable.
  mkdir -p ~/R

  # TODO: Add RUnit for devtools/R-test.sh
  INSTALL_DEST=$R_PATH Rscript -e 'install.packages(c("dplyr", "tidyr", "stringr"), lib=Sys.getenv("INSTALL_DEST"), repos="https://cloud.r-project.org")'

  # Note: The above doesn't seem to return non-zero status if there are
  # installation errors!

  # Explicit test copied from devtools/R-test.sh
  R_LIBS_USER=$R_PATH Rscript -e 'library(dplyr); library(tidyr); library(stringr); print("OK")'
}

"$@"
