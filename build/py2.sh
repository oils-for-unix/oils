# Usage: source build/py2.sh
#
# Duplicates build/dev-shell.sh, for _bin/shwrap stubs
#
# IMPORTANT: sourced by _build/oils.sh, so it must remain POSIX SHELL

ROOT_WEDGE_DIR=/wedge/oils-for-unix.org

# put 'python2' in $PATH
readonly _WEDGE_PY2_DIR=$ROOT_WEDGE_DIR/pkg/python2/2.7.18/bin
if test -d $_WEDGE_PY2_DIR; then
  export PATH="$_WEDGE_PY2_DIR:$PATH"
fi

