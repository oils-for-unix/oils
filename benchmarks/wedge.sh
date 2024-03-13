#!/usr/bin/env bash
#
# Analyze wedge build on Soil CI.
#
# Usage:
#   benchmarks/wedge.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

#source build/dev-shell.sh  # R_LIBS_USER


# Keeping ggplot2 out of the wedge until this works
install-R-packages() {
  mkdir -p ~/R
  INSTALL_DEST=~/R Rscript -e \
    'install.packages(c("dplyr", "ggplot2", "RUnit"), lib=Sys.getenv("INSTALL_DEST"), repos="https://cloud.r-project.org")'
}

readonly DIR=_tmp/wedge

download-tsv() {
  mkdir -p $DIR/{github,sourcehut}
  wget --directory-prefix $DIR/github \
    http://travis-ci.oilshell.org/github-jobs/6022/dev-setup-debian.wwz/_build/wedge/logs/tasks.tsv
  wget --directory-prefix $DIR/sourcehut \
    http://travis-ci.oilshell.org/srht-jobs/1138664/dev-setup-debian.wwz/_build/wedge/logs/tasks.tsv
}

plots() {
  #R_LIBS_USER=~/R benchmarks/wedge.R xargs-report _build/wedge/logs
  R_LIBS_USER=~/R benchmarks/wedge.R xargs-report $DIR/github
  R_LIBS_USER=~/R benchmarks/wedge.R xargs-report $DIR/sourcehut
}

"$@"
