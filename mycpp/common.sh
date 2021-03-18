#
# Common functions
#

# Include guard.
if test -n "${__MYCPP_COMMON_SH:-}"; then
  return
fi
readonly __MYCPP_COMMON_SH=1

if test -z "${REPO_ROOT:-}"; then
  echo "$REPO_ROOT should be set before sourcing"
  exit 1
fi

readonly MYPY_REPO=$REPO_ROOT/_clone/mypy

time-tsv() {
  $REPO_ROOT/benchmarks/time_.py --tsv "$@"
}
