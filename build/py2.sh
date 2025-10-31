# Usage: source build/py2.sh
#
# Duplicates build/dev-shell.sh, for _bin/shwrap stubs
#
# It's also sourced by _build/oils.sh via build/ninja-rules-cpp.sh, so it must
# remain POSIX SHELL.  That's for benchmarks/time_.py

# LEGACY
# put 'python2' in $PATH
ROOT_WEDGE_DIR=/wedge/oils-for-unix.org
readonly _WEDGE_PY2_DIR=$ROOT_WEDGE_DIR/pkg/python2/2.7.18/bin
if test -d $_WEDGE_PY2_DIR; then
  export PATH="$_WEDGE_PY2_DIR:$PATH"
fi

# 2025-10: also in build/dev-shell.sh
_DEPS_BIN_DIR=$PWD/../oils.DEPS/bin
if test -d $_DEPS_BIN_DIR; then
  export PATH="$_DEPS_BIN_DIR:$PATH"
fi
