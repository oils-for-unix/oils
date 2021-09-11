# Sets $PATH to the locations of some precompiled binaries.
# An alternative to nix-shell.
#
# Usage:
#   source build/dev-shell.sh
#
# Note: assumes that $REPO_ROOT is $PWD.

# build/codegen.sh builds binaries
readonly RE2C_DIR="$PWD/_deps/re2c-1.0.3"

# FALLBACK without test/spec-bin: test/spec.sh link-busybox-ash
readonly ASH_SYMLINK_DIR="$PWD/_tmp/shells"

# test/spec-bin.sh builds binaries
readonly SPEC_DIR="$PWD/_deps/spec-bin"

if test -d $RE2C_DIR; then
  export PATH="$RE2C_DIR:$PATH"
fi

if test -d $ASH_SYMLINK_DIR; then
  export PATH="$ASH_SYMLINK_DIR:$PATH"
fi

# This should override $ASH_SYMLINK_DIR
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

