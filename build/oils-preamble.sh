#!/bin/sh
#
# __FILE_COMMENT__
#
# For usage, run:
#
#   _build/oils.sh --help

. build/ninja-rules-cpp.sh

show_help() {
  cat <<'EOF'
Compile the oils-for-unix source into an executable.

Usage:
  _build/oils.sh COMPILER? VARIANT? TRANSLATOR? SKIP_REBUILD?

  COMPILER: 'cxx' for system compiler, 'clang' or custom one [default cxx]
  VARIANT: 'dbg' or 'opt' [default opt]
  TRANSLATOR: 'mycpp' or 'mycpp-souffle' [default mycpp]
  SKIP_REBUILD: if non-empty, checks if the output exists before building

Environment variable respected:

  OILS_PARALLEL_BUILD=
  BASE_CXXFLAGS=        # See build/ninja-rules-cpp.sh for details
  CXXFLAGS=
  OILS_CXX_VERBOSE=

EOF
}

parse_flags() {
  while true; do
    # ${1:-} needed for set -u
    case "${1:-}" in
      '')
        break
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        die "Invalid argument '$1'"
        ;;
    esac
    shift
  done
}


OILS_PARALLEL_BUILD=${OILS_PARALLEL_BUILD:-1}

_compile_one() {
  local src=$4

  echo "CXX $src"

  # Delegate to function in build/ninja-rules-cpp.sh
  if test "${_do_fork:-}" = 1; then
    compile_one "$@" &   # we will wait later
  else
    compile_one "$@"
  fi
}
