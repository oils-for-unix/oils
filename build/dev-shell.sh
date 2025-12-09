# Sets $PATH to the locations of some precompiled binaries.
# An alternative to nix-shell.
#
# Also sets PYTHONPATH and R_LIBS_USER
#
# Note: must run under /bin/sh, because _bin/shwrap/* tools use /bin/sh
#
# Usage:
#   source build/dev-shell.sh
#
# Notes:
# - assumes that $REPO_ROOT is $PWD.
# - build/py2.sh is a slimmer version, for just python2

# Include guard
test -n "${__BUILD_DEV_SHELL_SH:-}" && return
readonly __BUILD_DEV_SHELL_SH=1

# Used by BOTH this file, build/old-wedges.sh 
_MYPY_VERSION=0.780
_PY3_LIBS_VERSION=2023-03-04
_SITE_PACKAGES=lib/python3.10/site-packages

# So we can run Python 2 scripts directly, e.g. asdl/asdl_main.py
# Must come before old-wedges.sh
PYTHONPATH='.'

#
# PATH for old wedges - not available in Soil CI, but are on contributor machines
#

_OLD_WEDGES=build/old-wedges.sh
if test -f $_OLD_WEDGES; then
  # note: 'source' doesn't work under /bin/sh
  . $_OLD_WEDGES
fi

#
# PATH for 2025 wedges
#

_DEPS_BIN_DIR=$PWD/../oils.DEPS/bin
if test -d $_DEPS_BIN_DIR; then
  PATH="$_DEPS_BIN_DIR:$PATH"
fi

#
# R_LIBS_USER
#

_NEW_WEDGE_DIR=$PWD/../oils.DEPS/wedge
if test -d $_NEW_WEDGE_DIR/R-libs; then
  R_LIBS_USER=$_NEW_WEDGE_DIR/R-libs/2023-04-18
fi

#
# PYTHONPATH
#

# Unconditionally add to PYTHONPATH, to avoid ordering issues in initial build/deps.sh setup
readonly _NEW_PY3_LIBS_WEDGE=$_NEW_WEDGE_DIR/py3-libs/$_PY3_LIBS_VERSION/$_SITE_PACKAGES
PYTHONPATH="$_NEW_PY3_LIBS_WEDGE:$PYTHONPATH"

readonly _NEW_MYPY_WEDGE=$_NEW_WEDGE_DIR/mypy/$_MYPY_VERSION
if test -d "$_NEW_MYPY_WEDGE"; then
  PYTHONPATH="$_NEW_MYPY_WEDGE:$PYTHONPATH"
fi

# Hack for misconfigured RC cluster!  Some machines have the empty string in
# their $PATH (due to some having CUDA and others not).
#
# TODO: I should fix the machines, and make this a FATAL error.  The $PATH
# leaks on purpose because we might want to run with nix-shell -- see
# test/spec-common.sh.
case $PATH in
  *::*)
    PATH=$(echo "$PATH" | sed 's/::/:/g')
    ;;
esac

#
# Export all vars MUTATED
#

# Some of them might be exported already, but that's OK
export PATH PYTHONPATH R_LIBS_USER
