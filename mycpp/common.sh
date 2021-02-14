#
# Common functions
#

# Include guard.
test -n "${__MYCPP_COMMON_SH:-}" && return
readonly __MYCPP_COMMON_SH=1

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

# Could also be in _clone
readonly MYPY_REPO=${MYPY_REPO:-~/git/languages/mypy}

time-tsv() {
  $REPO_ROOT/benchmarks/time_.py --tsv "$@"
}

