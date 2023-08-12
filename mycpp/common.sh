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

source mycpp/common-vars.sh

maybe-our-python3() {
  ### Run a command line with Python 3

  # Use Python 3.10 from deps/from-tar if available.  Otherwise use the system
  # python3.

  local py3_ours='../oil_DEPS/python3'
  if test -f $py3_ours; then
    echo "*** Running $py3_ours $@" >& 2
    $py3_ours "$@"
  else
    # Use system copy
    python3 "$@"
  fi
}

