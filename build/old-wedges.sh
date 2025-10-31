# Old shell state, preserved to avoid breaking existing contributors.
#
# Usage:
#   source build/old-wedges.sh

# put 'python2' in $PATH
readonly WEDGE_PY2_DIR=$ROOT_WEDGE_DIR/pkg/python2/2.7.18/bin
if test -d $WEDGE_PY2_DIR; then
  PATH="$WEDGE_PY2_DIR:$PATH"
fi

# put 'python3' in $PATH
readonly WEDGE_PY3_DIR=$ROOT_WEDGE_DIR/pkg/python3/3.10.4/bin
# Unconditionally add it to PATH; otherwise build/deps.sh install-wedges won't
# work
PATH="$WEDGE_PY3_DIR:$PATH"

readonly WEDGE_RE2C_DIR=$ROOT_WEDGE_DIR/pkg/re2c/3.0/bin
if test -d $WEDGE_RE2C_DIR; then
  PATH="$WEDGE_RE2C_DIR:$PATH"
fi

readonly UFTRACE_WEDGE_DIR=$ROOT_WEDGE_DIR/pkg/uftrace/0.13/bin
if test -d $UFTRACE_WEDGE_DIR; then
  PATH="$UFTRACE_WEDGE_DIR:$PATH"
fi

# FALLBACK without busybox wedge: test/spec.sh link-busybox-ash
readonly ASH_SYMLINK_DIR="$PWD/_tmp/shells"
if test -d $ASH_SYMLINK_DIR; then
  PATH="$ASH_SYMLINK_DIR:$PATH"
fi

readonly WEDGE_SOUFFLE_DIR=$USER_WEDGE_DIR/pkg/souffle/2.4.1/bin
if test -d $WEDGE_SOUFFLE_DIR; then
  PATH="$WEDGE_SOUFFLE_DIR:$PATH"
fi

# OBSOLETE
# This takes precedence over $ASH_SYMLINK_DIR
readonly SPEC_DIR="$PWD/../oil_DEPS/spec-bin"

if test -d $SPEC_DIR; then
  PATH="$SPEC_DIR:$PATH"
fi

#
# NEW spec-bin wedges found before old ../oil_DEPS
#

readonly BASH_WEDGE_DIR=$USER_WEDGE_DIR/pkg/bash/4.4/bin
if test -d $BASH_WEDGE_DIR; then
  PATH="$BASH_WEDGE_DIR:$PATH"
fi

# bash 5 found before bash 4
readonly BASH5_WEDGE_DIR=$USER_WEDGE_DIR/pkg/bash/5.2.21/bin
if test -d $BASH5_WEDGE_DIR; then
  PATH="$BASH5_WEDGE_DIR:$PATH"
fi

readonly DASH_WEDGE_DIR=$USER_WEDGE_DIR/pkg/dash/0.5.10.2/bin
if test -d $DASH_WEDGE_DIR; then
  PATH="$DASH_WEDGE_DIR:$PATH"
fi

readonly MKSH_WEDGE_DIR=$USER_WEDGE_DIR/pkg/mksh/R52c
if test -d $MKSH_WEDGE_DIR; then
  PATH="$MKSH_WEDGE_DIR:$PATH"
fi

readonly ZSH_NEW_WEDGE_DIR=$USER_WEDGE_DIR/pkg/zsh/5.9/bin
if test -d $ZSH_NEW_WEDGE_DIR; then
  PATH="$ZSH_NEW_WEDGE_DIR:$PATH"
fi

# Old version comes first
readonly ZSH_OLD_WEDGE_DIR=$USER_WEDGE_DIR/pkg/zsh/5.1.1/bin
if test -d $ZSH_OLD_WEDGE_DIR; then
  PATH="$ZSH_OLD_WEDGE_DIR:$PATH"
fi

readonly BUSYBOX_WEDGE_DIR=$USER_WEDGE_DIR/pkg/busybox/1.35.0
if test -d $BUSYBOX_WEDGE_DIR; then
  PATH="$BUSYBOX_WEDGE_DIR:$PATH"
fi

readonly YASH_WEDGE_DIR=$USER_WEDGE_DIR/pkg/yash/2.49/bin
if test -d $YASH_WEDGE_DIR; then
  PATH="$YASH_WEDGE_DIR:$PATH"
fi

#
# R_LIBS_USER
#

OLD_WEDGE_DIR=~/wedge/oils-for-unix.org/pkg
if test -d ~/R; then
  # 2023-07: Hack to keep using old versions on lenny.local
  # In 2023-04, dplyr stopped supporting R 3.4.4 on Ubuntu Bionic
  # https://cran.r-project.org/web/packages/dplyr/index.html
  R_LIBS_USER=~/R
elif test -d $OLD_WEDGE_DIR/R-libs; then
  R_LIBS_USER=$OLD_WEDGE_DIR/R-libs/2023-04-18
fi
