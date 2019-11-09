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

source $THIS_DIR/common.sh  # oil-python-sources
source $THIS_DIR/../build/common.sh  # for OIL_SYMLINKS

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

    # TODO: Get rid of stdlib (compile) and compiler2.  Now that OPy works, we
    # just want opy and ccompile.

    if test $version = ccompile; then
      misc/ccompile.py $src_tree/${rel_path} $dest
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
# Used by the Makefile.
compile-manifest() {
  local dest_dir=$1

  # Python 2.7.14 on Ubuntu 17.10: ./regtest.sh verify-golden doesn't work.
  # Many diffs.
  # Our own Python 2.7.13: doesn't work.
  #local py=../_devbuild/cpython-full/python

  # Our own Python 2.7.12: Just one diff in hashlib.pyc!
  #local py=../_devbuild/cpython-full-2712/python

  local py=''

  while read full_src_path rel_dest_path; do
    local dest=$dest_dir/$rel_dest_path
    mkdir -p $(dirname $dest)
    log "     $full_src_path"

    # Save space by omitting docstring.
    $py $THIS_DIR/../bin/opyc compile -emit-docstring=0 $full_src_path $dest

    local rel_py_path=${rel_dest_path%.pyc}.py   # .pyc -> py

    # .pyc manifest to include in zip files
    echo $dest $rel_dest_path
    echo $full_src_path $rel_py_path
  done
}

# UNUSED
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

# TODO: This should be for unit tests only.  Probably don't need "mains".
#
# It overlaps with the normal build.  This is like build/oil-manifest.txt, but
# it's missing some stuff like the help.  The Makefile rule for
# _build/oil/bytecode.zip calls actions.sh files-manifest.
#
# Instead of printing .pyc, modify build/app_deps.py to print _tmp/oil/*.pyc !

_fill-oil-tree() {
  local dir=${1:-_tmp/repo-with-opy}

  mkdir -p $dir/_devbuild/help
  # For help text.
  cp -v ../_devbuild/help/* $dir/_devbuild/help

  cp -v ../asdl/*.asdl $dir/asdl
  ln -v -s -f $PWD/../{libc,fastlex}.so $dir
  ln -v -s -f $PWD/../oil-version.txt $dir

  # OPy needs this for the grammar pickle?  Maybe just copy it.
  ln -v -s -f --no-target-directory $PWD/../_build $dir/_build

  # Running core/process_test.py depends on this existing!
  mkdir -v -p $dir/_tmp

  local stub=$dir/bin/osh-byterun
  cat >$stub <<'EOF'
#!/bin/bash
readonly THIS_DIR=$(cd $(dirname $0) && pwd)
exec python $THIS_DIR/opy_.pyc opyc run $THIS_DIR/oil.pyc osh "$@"
EOF
  chmod +x $stub

  #make-mains $dir
}

# Compile with both compile() and OPy.
# TODO:
# - What about the standard library?  The whole app bundle should be
# compiled with OPy.
# - This could be part of the Travis build.  It will ensure no Python 2
# print statements sneak in.
oil-repo() {
  local repo_root=$(cd $THIS_DIR/.. && pwd)
  local files=( $(oil-python-sources $repo_root) )  # array

  _compile-tree $repo_root _tmp/repo-with-cpython/ ccompile "${files[@]}"
  _compile-tree $repo_root _tmp/repo-with-opy/ opy "${files[@]}"

  _fill-oil-tree _tmp/repo-with-cpython
  _fill-oil-tree _tmp/repo-with-opy
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

astgen() {
  tools/astgen.py tools/ast.txt > compiler2/ast.py
}

"$@"

