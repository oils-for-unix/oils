# Sets $PATH to the locations of some precompiled binaries.
# An alternative to nix-shell.
#
# Usage:
#   source build/dev-shell.sh
#
# Note: assumes that $REPO_ROOT is $PWD.
#
# IMPORTANT: sourced by _build/oils.sh, so it must remain POSIX SHELL

ROOT_WEDGE_DIR=/wedge/oils-for-unix.org
# Also in build/deps.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org

# put 'python2' in $PATH
readonly WEDGE_PY2_DIR=$ROOT_WEDGE_DIR/pkg/python2/2.7.18/bin
if test -d $WEDGE_PY2_DIR; then
  export PATH="$WEDGE_PY2_DIR:$PATH"
fi

# put 'python3' in $PATH
readonly WEDGE_PY3_DIR=$ROOT_WEDGE_DIR/pkg/python3/3.10.4/bin
if test -d $WEDGE_PY3_DIR; then
  export PATH="$WEDGE_PY3_DIR:$PATH"
fi

readonly WEDGE_BLOATY_DIR=$ROOT_WEDGE_DIR/pkg/bloaty/1.1  # not in bin
if test -d $WEDGE_BLOATY_DIR; then
  export PATH="$WEDGE_BLOATY_DIR:$PATH"
fi

readonly WEDGE_RE2C_DIR=$ROOT_WEDGE_DIR/pkg/re2c/3.0/bin
if test -d $WEDGE_RE2C_DIR; then
  export PATH="$WEDGE_RE2C_DIR:$PATH"
fi

# uftrace must be installed by wedge?
readonly UFTRACE_WEDGE_DIR=$ROOT_WEDGE_DIR/pkg/uftrace/0.13/bin
if test -d $UFTRACE_WEDGE_DIR; then
  export PATH="$UFTRACE_WEDGE_DIR:$PATH"
fi

# FALLBACK without test/spec-bin: test/spec.sh link-busybox-ash
readonly ASH_SYMLINK_DIR="$PWD/_tmp/shells"
if test -d $ASH_SYMLINK_DIR; then
  export PATH="$ASH_SYMLINK_DIR:$PATH"
fi

# test/spec-bin.sh builds binaries
# This takes precedence over $ASH_SYMLINK_DIR
readonly SPEC_DIR="$PWD/../oil_DEPS/spec-bin"

if test -d $SPEC_DIR; then
  export PATH="$SPEC_DIR:$PATH"
fi

R_LIBS_WEDGE=~/wedge/oils-for-unix.org/pkg/R-libs/2023-04-18
user=$(whoami)  # somehow $USER is not available in CI

if test $user = uke; then
  # in the CI
  export R_LIBS_USER=$R_LIBS_WEDGE
else
  # version matching on host doesn't work
  export R_LIBS_USER=~/R
fi

# So we can run Python 2 scripts directly, e.g. asdl/asdl_main.py
export PYTHONPATH='.'

# We can also run mycpp/mycpp_main.py directly
#
# But NOT bin/oils_for_unix.py (Python 2).  Those need to find our stripped down
# vendor/typing.py, but we CANNOT put vendor/ in $PYTHONPATH, because then
# mycpp would import it and fail.

readonly site_packages=lib/python3.10/site-packages

readonly PY3_LIBS_WEDGE=$USER_WEDGE_DIR/pkg/py3-libs/2023-03-04/$site_packages
if test -d "$PY3_LIBS_WEDGE"; then
  export PYTHONPATH="$PY3_LIBS_WEDGE:$PYTHONPATH"
fi

readonly MYPY_VERSION=0.780
# TODO: would be nice to upgrade to newer version
#readonly MYPY_VERSION=0.971

# Containers copy it here
readonly MYPY_WEDGE=$USER_WEDGE_DIR/pkg/mypy/$MYPY_VERSION
if test -d "$MYPY_WEDGE"; then
  export PYTHONPATH="$MYPY_WEDGE:$PYTHONPATH"
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
