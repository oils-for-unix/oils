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
  _build/oils.sh FLAGS* 
  _build/oils.sh --help

Flags:

  --cxx CXX [default 'cxx']
    The C++ compiler to use: 'cxx' for system compiler, 'clang', or custom string

  --variant ARG [default 'opt']
    The build variant, e.g. dbg, opt, asan

  --translator ARG [default 'mycpp']
    Which bundle of translated source code to compile: mycpp, mycpp-souffle

  --skip-rebuild
    If the output exists, skip the build

Environment variable respected:

  OILS_PARALLEL_BUILD=
  BASE_CXXFLAGS=        # See build/ninja-rules-cpp.sh for details
  CXXFLAGS=
  OILS_CXX_VERBOSE=

EOF
}

FLAG_cxx=cxx           # default is system compiler
FLAG_variant=opt       # default is optimized build

FLAG_translator=mycpp  # or mycpp-souffle
FLAG_skip_rebuild=''   # false

parse_flags() {
  # Note: not supporting --cxx=foo like ./configure, only --cxx foo

  while true; do
    # ${1:-} needed for set -u
    case "${1:-}" in
      '')
        break
        ;;

      -h|--help)
        show_help
        exit 0
        ;;

      --cxx)
        if test $# -eq 1; then
          die "--cxx requires an argument"
        fi
        shift
        FLAG_cxx=$1
        ;;

      --variant)
        if test $# -eq 1; then
          die "--variant requires an argument"
        fi
        shift
        FLAG_variant=$1
        ;;

      --translator)
        if test $# -eq 1; then
          die "--translator requires an argument"
        fi
        shift
        FLAG_translator=$1
        ;;

      --skip-rebuild)
        FLAG_skip_rebuild=true
        ;;

      *)
        die "Invalid argument '$1'"
        ;;
    esac
    shift
  done

  # legacy interface
  FLAG_cxx=${1:-$FLAG_cxx}
  FLAG_variant=${2:-$FLAG_variant}
  FLAG_translator=${3:-$FLAG_translator}
  FLAG_skip_rebuild=${4:-$FLAG_skip_rebuild}
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
