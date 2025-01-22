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
  _build/oils.sh FLAG* 
  _build/oils.sh --help

Flags:

  --cxx CXX [default 'cxx']
    The C++ compiler to use: 'cxx' for system compiler, 'clang', or custom
    string
  
  --variant ARG [default 'opt']
    The build variant, e.g. dbg, opt, asan, which adds compile and link flags.

  --translator ARG [default 'mycpp']
    Which bundle of translated source code to compile: mycpp, mycpp-souffle

  --skip-rebuild
    If the output exists, skip the build

Env vars respected:

  OILS_PARALLEL_BUILD= [default 1]
    Set to 0 to disable parallel compilation.

  OILS_CXX_VERBOSE=    [default '']
    Set to 1 to show build details.

Compile/link flags:

  BASE_CXXFLAGS=       (defined in build/common.sh)
    Override this to disable basic flags like -fno-omit-frame-pointer

  CXXFLAGS=            [default ''] (defined in build/ninja-rules-cpp.sh)
    Space-separated list of more compiler flags

  LDFLAGS=             [default ''] (defined in build/ninja-rules-cpp.sh)
    Space-separated list of more linker flags

Compiler flags come from 4 sources:

  1. The $BASE_CXXFLAGS var
  2. -I $REPO_ROOT is hard-coded
  3. The build --variant, e.g. 'asan' adds -fsanitizer=address and more
  4. The $CXXFLAGS var

Linker flags come from 3 sources:

  1. The build --variant, e.g. 'asan' adds -fsanitizer=address
  2. $STRIP_FLAGS, a variable detected by ./configure
  3. The $LDFLAGS var

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
