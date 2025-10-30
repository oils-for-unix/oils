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

# TODO: enable this include guard
#test -n "${__BUILD_DEV_SHELL_SH:-}" && return
#readonly __BUILD_DEV_SHELL_SH=1

#
# OLD WEDGES 
#

ROOT_WEDGE_DIR=/wedge/oils-for-unix.org
# Also in build/deps.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org

OLD_WEDGES=build/old-wedges.sh
if test -f $OLD_WEDGES; then
  # note: 'source' doesn't work under /bin/sh
  . $OLD_WEDGES
fi

#
# 2025 WEDGES
#

# Note:
# Should we have a command: deps/wedge.sh make-bin-dir 
# - happens in each docker build
# - happens in the contributor setup: build/deps.sh install-wedges

readonly DEPS_BIN_DIR=$PWD/../oils.DEPS/bin
if test -d $DEPS_BIN_DIR; then
  export PATH="$DEPS_BIN_DIR:$PATH"
fi

#
# Libraries: PYTHONPATH and R_LIBS_USER
#

OLD_WEDGE_DIR=~/wedge/oils-for-unix.org/pkg
NEW_WEDGE_DIR=$PWD/../oils.DEPS/wedge

if test -d ~/R; then
  # 2023-07: Hack to keep using old versions on lenny.local
  # In 2023-04, dplyr stopped supporting R 3.4.4 on Ubuntu Bionic
  # https://cran.r-project.org/web/packages/dplyr/index.html
  export R_LIBS_USER=~/R
elif test -d $NEW_WEDGE_DIR/R-libs; then
  export R_LIBS_USER=$NEW_WEDGE_DIR/R-libs/2023-04-18
elif test -d $OLD_WEDGE_DIR/R-libs; then
  export R_LIBS_USER=$OLD_WEDGE_DIR/R-libs/2023-04-18
fi

# So we can run Python 2 scripts directly, e.g. asdl/asdl_main.py
export PYTHONPATH='.'

# We can also run mycpp/mycpp_main.py directly
#
# But NOT bin/oils_for_unix.py (Python 2).  Those need to find our stripped down
# vendor/typing.py, but we CANNOT put vendor/ in $PYTHONPATH, because then
# mycpp would import it and fail.

readonly site_packages=lib/python3.10/site-packages

#readonly PY3_LIBS_VERSION=2023-07-27
readonly PY3_LIBS_VERSION=2023-03-04

readonly NEW_PY3_LIBS_WEDGE=$NEW_WEDGE_DIR/py3-libs/$PY3_LIBS_VERSION/$site_packages
readonly OLD_PY3_LIBS_WEDGE=$USER_WEDGE_DIR/pkg/py3-libs/$PY3_LIBS_VERSION/$site_packages
# Unconditionally add to PYTHONPATH; otherwise build/deps.sh install-wedges
# can't work in one shot
export PYTHONPATH="$NEW_PY3_LIBS_WEDGE:$OLD_PY3_LIBS_WEDGE:$PYTHONPATH"

MYPY_VERSION=0.780
# TODO: would be nice to upgrade to newer version
#readonly MYPY_VERSION=0.971

# Containers copy it here
readonly OLD_MYPY_WEDGE=$USER_WEDGE_DIR/pkg/mypy/$MYPY_VERSION
if test -d "$OLD_MYPY_WEDGE"; then
  export PYTHONPATH="$OLD_MYPY_WEDGE:$PYTHONPATH"
fi

readonly NEW_MYPY_WEDGE=$NEW_WEDGE_DIR/mypy/$MYPY_VERSION
if test -d "$NEW_MYPY_WEDGE"; then
  export PYTHONPATH="$NEW_MYPY_WEDGE:$PYTHONPATH"
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
