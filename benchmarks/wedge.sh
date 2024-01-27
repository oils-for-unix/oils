#!/usr/bin/env bash
#
# Analyze how mycpp speeds up programs.
#
# Usage:
#   benchmarks/mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source build/dev-shell.sh  # R_LIBS_USER
#source soil/common.sh  # find-dir-html
#source test/tsv-lib.sh  # tsv2html

xargs-report() {
  benchmarks/wedge.R xargs-report _build/wedge/logs
}

"$@"
