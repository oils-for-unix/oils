#!/bin/bash
#
# Build actions used in the Makefile.
#
# Usage:
#   ./actions.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

c-module-toc() {
  cd $PY27
  ../build/c_module_toc.py
}

# Modules needed to 'import runpy'.
runpy-deps() {
  $PREPARE_DIR/python -S build/runpy_deps.py "$@"
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

  # I need the right relative path for Oil
  ln -s -f $PWD/build/app_deps.py ~/git/oil/_tmp

  # Set _HAVE_READLINE env variable for Python.
  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S ~/git/oil/_tmp/app_deps.py $main_module $prefix

  source-detected-config-or-die  # for HAVE_READLINE

  # apps-deps-c.txt is for the developer building the tarball.
  # app-deps-to-compile.txt is for the end-user build.

  local out2=${prefix}-c.txt
  local out3=${prefix}-to-compile.txt
  if test "$HAVE_READLINE" = 1; then
    cat $out2 > $out3
  else
    # Don't fail if grep fails!
    grep -v 'readline' $out2 > $out3 || true
  fi
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
    echo "extern void init$mod(void);"
  done
}

initbits() {
  for mod in "$@"; do
    echo "    {\"$mod\", init$mod},"
  done
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
  local discovered=${2:-_tmp/oil/discovered-c.txt}

  # Filter out comments, print the first line.
  #
  # TODO: I don't want to depend on egrep and GNU flags on the target sytems?
  # Ship this file I guess.
  egrep --no-filename --only-matching '^[a-zA-Z_\.]+' $static $discovered \
    | sort | uniq
}

#
# Misc
#

# To test building stdlib.
clean-pyc() {
  find $PY27/Lib -name '*.pyc' | xargs --no-run-if-empty -- rm --verbose
}

"$@"
