#!/usr/bin/env bash
#
# Build actions used in the Makefile.
#
# Usage:
#   ./actions.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source build/common.sh

write-release-date() {
  mkdir -p _build  # Makefile makes this, but scripts/release.sh needs it too

  # Write a readable, sortable date that is independent of time zone.
  date --utc --rfc-3339 seconds > _build/release-date.txt
}

main-name() {
  local python_main=${1:-hello}
  local ovm_bundle_prefix=${2:-hello.ovm}

  cat <<EOF 
char* MAIN_NAME = "$python_main";
#if OVM_DEBUG
  char* OVM_BUNDLE_FILENAME = "${ovm_bundle_prefix}-dbg";
#else
  char* OVM_BUNDLE_FILENAME = "$ovm_bundle_prefix";
#endif
EOF
}

c-module-toc() {
  cd $PY27
  ../build/c_module_toc.py
}

# Modules needed to 'import runpy'.
runpy-deps() {
  $PREPARE_DIR/python -S build/runpy_deps.py both "$@"
}

runpy-py-to-compile() {
  $PREPARE_DIR/python -S build/runpy_deps.py py
}

# This version gets the paths out of the repo.  But it requires that we
# build all of Python!
#
# OK yeah so there are a few steps to building minimal app bundles.
# 1. Build all of Python normally.  Normal -D options.
#    ./run.sh build-clang-default
# 2. Then run a special build that is based on that.
#
# Only need a debug build.

# Run  grep -F .so  for the native dependencies.  Have to add those
# somewhere.
app-deps() {
  local app_name=${1:-hello}
  local pythonpath=${2:-build/testdata}
  local main_module=${3:-hello}

  local prefix=_build/$app_name/app-deps

  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S build/app_deps.py both $main_module $prefix
}

# .py files to compile
py-to-compile() {
  local pythonpath=${1:-build/testdata}
  local main_module=${2:-hello}

  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S build/app_deps.py py $main_module
}

# For embedding in oil/bytecode.zip.
help-manifest() {
  local dir=$1
  for path in $dir/*; do
    echo "$path $path"  # relative path is the same
  done
}

pyc-version-manifest() {
  local manifest_path=${1:-_build/oil/bytecode-opy-manifest.txt}  # For example

  # Just show a string like "bytecode-opy.zip" for now.  There is no OPy
  # version yet.
  local filename=$(basename $manifest_path) 
  local user_str=${filename%-manifest.txt}.zip
  local dir=$(dirname $manifest_path)

  echo $user_str > $dir/pyc-version.txt

  # Put it at the root, like release-date and oil-version.txt.
  echo $dir/pyc-version.txt pyc-version.txt
}

# Make .d file
make-dotd() {
  local app_name=${1:-hello}
  local app_deps_to_compile=${2:-_tmp/hello/app-deps-to-compile.txt}

  # TODO: For each module, look it up in the manifest.
  # I guess make a Python file.

  echo "# TODO $app_deps_to_compile"

  # The dependencies we want.
  # X to prevent screwing things up.
  echo "X_build/$app_name/ovm:"
  echo "X_build/$app_name/ovm-dbg:"
  echo "X_build/$app_name/ovm-cov:"
}

#
# C Code generation.  The three functions below are adapted from
# Modules/makesetup.
#

extdecls() {
  for mod in "$@"; do
    test "$mod" = line_input && echo "#ifdef HAVE_READLINE"
    echo "extern void init$mod(void);"
    test "$mod" = line_input && echo "#endif"
  done
  return 0  # because test can fail
}

initbits() {
  for mod in "$@"; do
    test "$mod" = line_input && echo "#ifdef HAVE_READLINE"
    echo "    {\"$mod\", init$mod},"
    test "$mod" = line_input && echo "#endif"
  done
  return 0  # because test can fail
}

# Ported from sed to awk.  Awk is MUCH nicer (no $NL ugliness, -v flag, etc.)
gen-module-init() {
  local extdecls
  extdecls=$(extdecls "$@")
  local initbits
  initbits=$(initbits "$@")

  local template=$PY27/Modules/config.c.in

  awk -v template=$template -v extdecls="$extdecls" -v initbits="$initbits" '
    BEGIN {
      print "/* Generated automatically from " template " */"
    }
    /MARKER 1/ {
      print extdecls
      next
    }
    /MARKER 2/ {
      print initbits
      next
    }
    {
      print $0
    }
    ' $template
}

#
# C Modules
#

join-modules() {
  local static=${1:-static-c-modules.txt}
  local discovered=${2:-_build/oil/all-deps-c.txt}

  # Filter out comments, print the first line.
  #
  # TODO: I don't want to depend on egrep and GNU flags on the target sytems?
  # Ship this file I guess.
  egrep --no-filename --only-matching '^[a-zA-Z0-9_\.]+' $static $discovered \
    | sort | uniq
}

#
# Misc
#

# To test building stdlib.
clean-pyc() {
  # skip _chroot, _tmp, etc.  But delete __init__.pyc
  find . \( -type d -a -name '_*' -a -prune \) -o -name '*.pyc' -a -print |
    xargs --no-run-if-empty -- rm --verbose
}

# NOTE: Not deleting _devbuild, including cpython-full.  Maybe we should, or
# we should put it in a different directory?
clean-repo() {
  clean-source-tarball-build
  rm -r -f -v _build _release
  rm -f -v _bin/hello.* _bin/opy.*
  clean-pyc
}

# 'make clean'.
# NOTE:
# - There are no object files written now.
# - We're not cleaning _build/detect-config.* ?
clean-source-tarball-build() {
  rm -f -v _bin/oil.{ovm,ovm-dbg}
  # NOTE: delete ovm-opt, ovm-opt.{stripped,symbols}
  rm -f -v \
      _build/oil/{ovm-opt,ovm-dbg} \
      _build/oil/ovm-opt.{stripped,symbols}
}

"$@"
