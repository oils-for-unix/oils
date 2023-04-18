# Sets $PATH to the locations of some precompiled binaries.
# An alternative to nix-shell.
#
# Usage:
#   source build/dev-shell.sh
#
# Note: assumes that $REPO_ROOT is $PWD.

# Old location for python3
readonly DEPS_DIR="$PWD/../oil_DEPS"
if test -f $DEPS_DIR/python3; then
  export PATH="$DEPS_DIR:$PATH"
fi

ROOT_WEDGE_DIR=/wedge/oils-for-unix.org
# Also in build/deps.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org

readonly WEDGE_PY3_DIR=$ROOT_WEDGE_DIR/pkg/python3/3.10.4/bin
if test -d $WEDGE_PY3_DIR; then
  export PATH="$WEDGE_PY3_DIR:$PATH"
fi

readonly WEDGE_BLOATY_DIR=$ROOT_WEDGE_DIR/pkg/bloaty/1.1  # not in bin
if test -d $WEDGE_BLOATY_DIR; then
  export PATH="$WEDGE_BLOATY_DIR:$PATH"
fi

# TODO: always use wedge dirs
readonly RE2C_DIR="$PWD/../oil_DEPS/re2c"
readonly WEDGE_RE2C_DIR=$ROOT_WEDGE_DIR/pkg/re2c/3.0/bin

if test -d $RE2C_DIR; then
  export PATH="$RE2C_DIR:$PATH"
elif test -d $WEDGE_RE2C_DIR; then
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

# Old location.  We are NOT using the venv bin/active -- only pointing at its
# libraries, because that's enough.
readonly OLD_MYCPP_VENV=$DEPS_DIR/mycpp-venv/$site_packages
if test -d "$OLD_MYCPP_VENV"; then
  export PYTHONPATH="$OLD_MYCPP_VENV:$PYTHONPATH"
fi

readonly PY3_LIBS_WEDGE=$USER_WEDGE_DIR/pkg/py3-libs/2023-03-04/$site_packages
if test -d "$PY3_LIBS_WEDGE"; then
  export PYTHONPATH="$PY3_LIBS_WEDGE:$PYTHONPATH"
fi

# Old location
readonly OLD_MYPY_REPO=$DEPS_DIR/mypy  # also defined in mycpp/common-vars.sh
if test -d "$OLD_MYPY_REPO"; then
  export PYTHONPATH="$OLD_MYPY_REPO:$PYTHONPATH"
fi

# Containers copy it here
readonly MYPY_WEDGE=$USER_WEDGE_DIR/pkg/mypy/0.780
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
