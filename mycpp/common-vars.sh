# POSIX shell script sourced by _bin/shwrap/mycpp_main and mycpp/common.sh

if test -z "${REPO_ROOT:-}"; then
  echo '$REPO_ROOT should be set before sourcing'
  exit 1
fi

readonly MYPY_REPO=$REPO_ROOT/../oil_DEPS/mypy
readonly MYCPP_VENV=$REPO_ROOT/../oil_DEPS/mycpp-venv

