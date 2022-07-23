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

# Used by cpp/test.sh and mycpp/test.sh

run-test() {
  local bin=$1
  local compiler=$2
  local variant=$3

  local dir=_test/$compiler-$variant/cpp

  mkdir -p $dir

  local name=$(basename $bin)
  export LLVM_PROFILE_FILE=$dir/$name.profraw

  local log=$dir/$name.log
  log "RUN $bin > $log"
  $bin > $log
}

