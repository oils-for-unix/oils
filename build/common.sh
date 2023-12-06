# Usage:
#   source build/common.sh

# Include guard.
test -n "${__BUILD_COMMON_SH:-}" && return
readonly __BUILD_COMMON_SH=1

if test -z "${REPO_ROOT:-}"; then
  echo 'build/common.sh: $REPO_ROOT should be set before sourcing'
  exit 1
fi

set -o nounset
set -o errexit
#eval 'set -o pipefail'

# New version is slightly slower -- 13 seconds vs. 11.6 seconds on oils-for-unix
readonly CLANG_DIR_RELATIVE='../oil_DEPS/clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04'

CLANG_DIR_1=$REPO_ROOT/$CLANG_DIR_RELATIVE
CLANG_DIR_FALLBACK=~/git/oilshell/oil/$CLANG_DIR_RELATIVE
if test -d $CLANG_DIR_1; then
  CLANG_DIR=$CLANG_DIR_1
  CLANG_IS_MISSING=''
else
  # BUG FIX: What if we're building _deps/ovm-build or ../benchmark-data/src?
  # Just hard-code an absolute path.  (We used to use $PWD, but I think that
  # was too fragile.)
  CLANG_DIR=$CLANG_DIR_FALLBACK
  CLANG_IS_MISSING='T'
fi
readonly CLANG_DIR

readonly CLANG=$CLANG_DIR/bin/clang  # used by benchmarks/{id,ovm-build}.sh
readonly CLANGXX=$CLANG_DIR/bin/clang++

# I'm not sure if there's a GCC version of this?
export ASAN_SYMBOLIZER_PATH=$CLANG_DIR_RELATIVE/bin/llvm-symbolizer

# ThreadSanitizer doesn't always give us all locations, but this doesn't help
# export TSAN_SYMBOLIZER_PATH=$ASAN_SYMBOLIZER_PATH

# equivalent of 'cc' for C++ language
# https://stackoverflow.com/questions/172587/what-is-the-difference-between-g-and-gcc
CXX=${CXX:-'c++'}

# Compiler flags we want everywhere.
# - -Weverything is more than -Wall, but too many errors now.
# - -fno-omit-frame-pointer is what Brendan Gregg says should always be on.
#   Omitting the frame pointer might be neglibly faster, but reduces
#   observability.  It's required for the 'perf' tool and other kinds of tracing.
#   Anecdotally the speed difference was in the noise on parsing
#   configure-coreutils.  
# - TODO(6/22): Disabled invalid-offsetof for now, but we should enable it after
#   progress on the garbage collector.  It could catch bugs.

# Allow user to override both BASE_CXXFLAGS and CXXFLAGS
# There doesn't seem to be a well-known convention for this.  Similar to this
# question:
# - https://stackoverflow.com/questions/51606653/allowing-users-to-override-cflags-cxxflags-and-friends

default_cxx_flags='-std=c++11 -Wall -Wno-invalid-offsetof -fno-omit-frame-pointer'

# note: Use - and not :- so that BASE_CXXFLAGS= works
BASE_CXXFLAGS=${BASE_CXXFLAGS-$default_cxx_flags}

readonly PY27=Python-2.7.13

readonly PREPARE_DIR=$REPO_ROOT/../oil_DEPS/cpython-full

log() {
  echo "$@" >&2
}

die() {
  log "$0: FATAL: $@"
  exit 1
}

can-compile-32-bit() {
  # Try compiling a basic file
  c++ -m32 -o /dev/null build/detect-cc.c
}
