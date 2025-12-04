#!/usr/bin/env bash
#
# Usage:
#   deps/make-bin.sh <function name>
#
# Examples:
#   deps/make-bin.sh contrib  # make symlinks in ../oils.DEPS/bin

set -o nounset
set -o pipefail
set -o errexit

# Note: versions are duplicated from build/deps.sh right now

link-relative() {
  ln -s -f --relative --verbose "$@"
}

re2c() {
  local deps_dir=$1
  link-relative $deps_dir/wedge/re2c/3.0/bin/re2c $deps_dir/bin 
}

python2() {
  ### duplicated from Dockerfile.soil-debian-12
  local deps_dir=$1

  # Make a python2 symlink only, NOT python
  link-relative $deps_dir/wedge/python2/2.7.18/bin/python $deps_dir/bin/python2
}

python3() {
  ### duplicated from Dockerfile.soil-debian-12
  local deps_dir=$1

  link-relative $deps_dir/wedge/python3/3.10.4/bin/python3 $deps_dir/bin
}

shells() {
  ### used in ovm-tarball
  local deps_dir=$1

  link-relative $deps_dir/wedge/bash/4.4/bin/bash $deps_dir/bin/bash-4.4
  link-relative $deps_dir/wedge/bash/5.2.21/bin/bash $deps_dir/bin/bash-5.2.21
  # newer bash 5.2  is the default
  link-relative $deps_dir/wedge/bash/5.2.21/bin/bash $deps_dir/bin/bash

  # symlink as ash
  link-relative $deps_dir/wedge/busybox/1.35.0/busybox $deps_dir/bin/ash

  link-relative $deps_dir/wedge/dash/0.5.10.2/bin/dash $deps_dir/bin
  link-relative $deps_dir/wedge/mksh/R52c/mksh $deps_dir/bin
  link-relative $deps_dir/wedge/yash/2.49/bin/yash $deps_dir/bin

  link-relative $deps_dir/wedge/zsh/5.1.1/bin/zsh $deps_dir/bin/zsh-5.1.1
  link-relative $deps_dir/wedge/zsh/5.9/bin/zsh $deps_dir/bin/zsh-5.9
  # older zsh 5.1.1 is the default
  link-relative $deps_dir/wedge/zsh/5.1.1/bin/zsh $deps_dir/bin/zsh
}

contrib() {
  ### What contributors need to run

  local deps_dir=../oils.DEPS

  mkdir -p $deps_dir/bin

  shells $deps_dir
  echo

  re2c $deps_dir
  python2 $deps_dir
  python3 $deps_dir

  # TODO: can move others
  #
  # Right now there are explicit paths in cmark.py and time_.py
  # - time-helper
  # - bin/cmark
  #
  # - bloaty
  # - uftrace
  # - flame graphs, etc.
}

extra() {
  # The release process depends on bloaty
  local deps_dir=../oils.DEPS

  link-relative $deps_dir/wedge/bloaty/1.1/bloaty $deps_dir/bin/bloaty
  link-relative $deps_dir/wedge/uftrace/0.13/bin/uftrace $deps_dir/bin/uftrace
}

"$@"
