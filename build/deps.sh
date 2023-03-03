#!/usr/bin/env bash
#
# Script for contributors to quickly set up core packages
#
# Usage:
#   build/deps.sh <function name>
#
# - re2c
# - cmark
# - python3
# - mypy and deps, so mycpp can import htem
#

set -o nounset
set -o pipefail
set -o errexit

readonly RE2C_VERSION=3.0
readonly RE2C_URL="https://github.com/skvadrik/re2c/releases/download/$RE2C_VERSION/re2c-$RE2C_VERSION.tar.xz"

readonly CMARK_VERSION=0.29.0
readonly CMARK_URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

readonly PY3_VERSION=3.10.4
readonly PY3_URL="https://www.python.org/ftp/python/3.10.4/Python-$PY3_VERSION.tar.xz"

die() {
  echo "$@" >& 2
  exit 1
}

download-to() {
  local dir=$1
  local url=$2
  wget --no-clobber --directory "$dir" "$url"
}

maybe-extract() {
  local wedge_dir=$1
  local tar_name=$2
  local out_dir=$3

  if test -d "$wedge_dir/$out_dir"; then
    echo "Not extracting because $wedge_dir/$out_dir exists"
    return
  fi

  local tar=$wedge_dir/$tar_name
  case $tar_name in
    *.gz)
      flag='--gzip'
      ;;
    *.bz2)
      flag='--bzip2'
      ;;
    *.xz)
      flag='--xz'
      ;;
    *)
      die "tar with unknown extension: $tar_name"
      ;;
  esac

  tar --extract $flag --file $tar --directory $wedge_dir
}

clone-mypy() {
  ### replaces deps/from-git
  local dest_dir=$1
  local version=0.780

  local dest=$dest_dir/mypy-$version
  if test -d $dest; then
    echo "Not cloning because $dest exists"
    return
  fi

  # TODO: verify commit checksum
  git clone --recursive --depth=50 --branch=release-$version \
    https://github.com/python/mypy $dest
}

fetch() {
  # For now, simulate what 'medo sync deps/source.medo _build/deps-source'
  # would do: fetch compressed tarballs designated by .treeptr files, and
  # expand them.

  # _build/deps-source/
  #   re2c/
  #     WEDGE
  #     re2c-3.0/  # expanded .tar.xz file

  local base_dir=_build/deps-source
  mkdir -p $base_dir

  # Copy the whole tree, including the .treeptr files
  cp --verbose --recursive --no-target-directory \
    deps/source.medo/ $base_dir/

  download-to $base_dir/re2c "$RE2C_URL"
  download-to $base_dir/cmark "$CMARK_URL"
  download-to $base_dir/python3 "$PY3_URL"

  maybe-extract $base_dir/re2c "$(basename $RE2C_URL)" re2c-$RE2C_VERSION
  maybe-extract $base_dir/cmark "$(basename $CMARK_URL)" cmark-$CMARK_VERSION
  maybe-extract $base_dir/python3 "$(basename $PY3_URL)" Python-$PY3_VERSION

  clone-mypy $base_dir/mypy

  if command -v tree > /dev/null; then
    tree -L 2 $base_dir
  fi
}

install() {
  # TODO:
  # - Make all of these RELATIVE wedges
  # - Add
  #   - unboxed-rel-smoke-test -- move it inside container
  #   - rel-smoke-test -- mount it in a different location

  deps/wedge.sh unboxed-build _build/deps-source/re2c/
  deps/wedge.sh unboxed-build _build/deps-source/cmark/
  deps/wedge.sh unboxed-build _build/deps-source/python3/

  # Depends on source.medo/mypy, which uses the git repo
  deps/wedge.sh unboxed-build _build/deps-source/mypy-venv/
}

"$@"
