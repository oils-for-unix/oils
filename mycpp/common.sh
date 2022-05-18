#
# Common functions
#

# Include guard.
test -n "${__MYCPP_COMMON_SH:-}" && return
readonly __MYCPP_COMMON_SH=1

if test -z "${REPO_ROOT:-}"; then
  echo '$REPO_ROOT should be set before sourcing'
  exit 1
fi

readonly MYPY_REPO=$REPO_ROOT/../oil_DEPS/mypy
readonly MYCPP_VENV=$REPO_ROOT/../oil_DEPS/mycpp-venv
