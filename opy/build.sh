#!/usr/bin/env bash
#
# Compile Python code with OPy.
#
# NOTE: this is roughly analogous to build/actions.sh and may be moved
# there.
#
# Usage:
#   ./build.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)

source $THIS_DIR/common.sh
source $THIS_DIR/../build/common.sh  # for OIL_SYMLINKS

grammar() {
  mkdir -p _tmp
  opy_ pgen2 $THIS_DIR/py27.grammar $THIS_DIR/$GRAMMAR
}

md5-manifest() {
  local tree=$1
  pushd $tree
  # size and name
  find . -type f | sort | xargs stat --format '%s %n' | tee SIZES.txt
  find . -type f | sort | xargs md5sum | tee MD5.txt
  popd
}

_compile-tree() {
  local src_tree=$1
  local dest_tree=$2
  local version=$3
  shift 3

  rm -r -f $dest_tree

  #local ext=opyc
  local ext=pyc

  for rel_path in "$@"; do
    echo $rel_path
    local dest=${dest_tree}/${rel_path%.py}.${ext}
    mkdir -p $(dirname $dest)

    if test $version = stdlib; then
      _stdlib-compile-one $src_tree/${rel_path} $dest
    elif test $version = compiler2; then
      _compile2-one $src_tree/${rel_path} $dest
    elif test $version = ccompile; then
      _ccompile-one $src_tree/${rel_path} $dest
    elif test $version = opy; then
      $THIS_DIR/../bin/opyc compile $src_tree/${rel_path} $dest
    else
      die "bad"
    fi
  done

  tree $dest_tree
  md5-manifest $dest_tree
}

# Like _compile-tree, but takes pairs on stdin.
compile-manifest() {
  local dest_dir=$1
  while read full_src_path rel_dest_path; do
    local dest=$dest_dir/$rel_dest_path
    mkdir -p $(dirname $dest)
    log "     $full_src_path"
    bin/opyc compile $full_src_path $dest

    local rel_py_path=${rel_dest_path%.pyc}.py   # .pyc -> py

    # .pyc manifest to include in zip files
    echo $dest $rel_dest_path
    echo $full_src_path $rel_py_path
  done
}

make-mains() {
  local dir=${1:-_tmp/oil-opy}

  # Have to use shells cripts rather than symlinks because .pyc files aren't
  # executable.
  # TODO: Use oil.ovm instead of system Python.
  for link in "${OIL_SYMLINKS[@]}"; do
    { echo '#!/bin/sh'
      echo "main=$link"
      echo 'exec python $(dirname $0)/oil.pyc $main "$@"'
    } >$dir/bin/$link

    chmod --verbose +x $dir/bin/$link
  done
}

# TODO: Consolidate with the normal build.  This is like
# build/oil-manifest.txt.  The Makefile rule for _build/oil/bytecode.zip calls
# actions.sh files-manifest.
#
# Instead of printing .pyc, modify build/app_deps.py to print _tmp/oil/*.pyc !
#
# And then write a script to run spec tests against the oil-opy.ovm debug
# oil1.ovm
# oil1.ovm-dbg
#
# oil-with-cpython.ovm
# oil-with-cpython.ovm-dbg

_fill-oil-tree() {
  local dir=${1:-_tmp/oil-opy}

  cp -v ../osh/{osh,types}.asdl $dir/osh
  cp -v ../core/runtime.asdl $dir/core
  cp -v ../asdl/arith.asdl $dir/asdl
  ln -v -s -f $PWD/../{libc,fastlex}.so $dir
  ln -v -s -f $PWD/../oil-version.txt $dir

  # Needed for help text.
  ln -v -s -f --no-target-directory $PWD/../_build $dir/_build

  make-mains $dir
}

# Compile with both compile() and OPy.
# TODO:
# - What about the standard library?  The whole app bundle should be
# compiled with OPy.
# - This could be part of the Travis build.  It will ensure no Python 2
# print statements sneak in.
oil-repo() {
  local src=$(cd .. && echo $PWD)

  # NOTE: Exclude _devbuild/cpython-full, but include _devbuild/gen.
  local files=( $(find $src \
              -name _tmp -a -prune -o \
              -name _chroot -a -prune -o \
              -name cpython-full -a -prune -o \
              -name _deps -a -prune -o \
              -name Python-2.7.13 -a -prune -o \
              -name opy -a -prune -o \
              -name 'test' -a -prune -o \
              -name '*.py' -a -printf '%P\n') )

  _compile-tree $src _tmp/oil-ccompile/ ccompile "${files[@]}"
  _compile-tree $src _tmp/oil-opy/ opy "${files[@]}"

  _fill-oil-tree _tmp/oil-ccompile/ 
  _fill-oil-tree _tmp/oil-opy/

  #_compile-tree $src _tmp/osh-compile2/ compiler2 "${files[@]}"

  # Not deterministic!
  #_compile-tree $src _tmp/osh-compile2.gold/ compiler2 "${files[@]}"
  #_compile-tree $src _tmp/osh-stdlib/ stdlib "${files[@]}"
}

_oil-bin-manifest() {
  # NOTE: These need to be made unique.  build/make_zip.py, but our shell
  # alias doesn't.
  # For some reason sys.modules has different modules with the same __file__.

  { build/actions.sh runpy-py-to-compile
    build/actions.sh py-to-compile '.' 'bin.oil'
  } | sort | uniq
}

oil-bin() {
  pushd $THIS_DIR/.. >/dev/null
  _oil-bin-manifest | compile-manifest _tmp/oil-with-opy
  popd >/dev/null
}

_opy-bin-manifest() {
  build/actions.sh py-to-compile '.' 'bin.opy_'
}

opy-bin() {
  pushd .. >/dev/null
  _opy-bin-manifest | compile-manifest _tmp/opy-with-opy
  popd >/dev/null
}

"$@"

