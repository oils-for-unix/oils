# Sets $PATH to the locations of some precompiled binaries.
# An alternative to nix-shell.
#
# Usage:
#   source build/dev-shell.sh
#
# Note: assumes that $REPO_ROOT is $PWD.

# TODO: Move everything into 'bin'
readonly DEPS_BIN_DIR="$PWD/../oil_DEPS/bin"
if test -d $DEPS_BIN_DIR; then
  export PATH="$DEPS_BIN_DIR:$PATH"
fi

readonly WEDGE_BLOATY_DIR=/wedge/oils-for-unix.org/pkg/bloaty/1.1  # not in bin
if test -d $WEDGE_BLOATY_DIR; then
  export PATH="$WEDGE_BLOATY_DIR:$PATH"
fi

# TODO: always use wedge dirs
readonly RE2C_DIR="$PWD/../oil_DEPS/re2c"
readonly WEDGE_RE2C_DIR=/wedge/oils-for-unix.org/pkg/re2c/3.0/bin

if test -d $RE2C_DIR; then
  export PATH="$RE2C_DIR:$PATH"
elif test -d $WEDGE_RE2C_DIR; then
  export PATH="$WEDGE_RE2C_DIR:$PATH"
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

# Hack for misconfigured RC cluster!  Some machines have the empty string in
# their $PATH (due to some having CUDA and others not).
#
# TODO: I should fix the machines, and make this a FATAL error.  The $PATH
# leaks on purpose because we might want to run with nix-shell -- see
# test/spec-common.sh.
good_path=${PATH//::/:}
if test "$good_path" != "$PATH"; then
  #echo "Warning: Fixing PATH misconfigured with current dir: $PATH" >&2
  PATH=$good_path
fi

