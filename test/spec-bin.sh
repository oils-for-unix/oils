#!/usr/bin/env bash
#
# Build binaries for the spec tests.  This is necessary because they tickle
# behavior in minor versions of each shell.
#
# Usage:
#   test/spec-bin.sh <function name>
#
# Instructions:
#   test/spec-bin.sh download     # Get the right version of every tarball
#   test/spec-bin.sh extract-all  # Extract source
#   test/spec-bin.sh build-all    # Compile
#   test/spec-bin.sh copy-all     # Put them in ../oil_DEPS/spec-bin
#   test/spec-bin.sh test-all     # Run a small smoke test
#
# Once you've run all steps manually and understand how they work, run them
# all at once with:
#
#   test/spec-bin.sh all-steps

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source devtools/run-task.sh
source test/spec-common.sh

# This dir is a sibling to the repo to make it easier to use containers
readonly TAR_DIR=$REPO_ROOT/_cache/spec-bin
readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS/spec-bin

#
# "Non-hermetic"
#

link-busybox-ash() {
  ### Non-hermetic ash only used for benchmarks / Soil dev-minimal

  # Could delete this at some point
  mkdir -p _tmp/shells
  ln -s -f --verbose "$(which busybox)" _tmp/shells/ash
}

# dash and bash should be there by default on Ubuntu.
install-shells-with-apt() {
  ### Non-hermetic shells; test/spec-bin.sh replaces this for most purposes

  set -x  # show what needs sudo

  # pass -y to install in an automated way
  sudo apt "$@" install busybox-static mksh zsh
  set +x
  link-busybox-ash
}

#
# Our own hermetic copies
#

# The authoritative versions!
download() {
  mkdir -p $TAR_DIR

  # TODO: upgrade zsh and mksh

  wget --no-clobber --directory $TAR_DIR \
    https://www.oilshell.org/blob/spec-bin/$BASH_NAME.tar.gz \
    https://www.oilshell.org/blob/spec-bin/$BUSYBOX_NAME.tar.bz2 \
    https://www.oilshell.org/blob/spec-bin/$DASH_NAME.tar.gz \
    https://www.oilshell.org/blob/spec-bin/mksh-R52c.tgz \
    https://www.oilshell.org/blob/spec-bin/zsh-5.1.1.tar.xz \
    https://www.oilshell.org/blob/spec-bin/$YASH_NAME.tar.xz
}

extract-all() {
  pushd $TAR_DIR

  # Remove name collision: spec-bin/mksh could be a FILE and a DIRECTORY.
  # This is unfortunately how their tarball is laid out.
  rm --verbose -r -f mksh mksh-R52c

  for archive in *.tar.* *.tgz; do
    echo $archive
    tar --extract --file $archive
  done
  mv --verbose --no-target-directory mksh mksh-R52c  # so it doesn't collide
  popd
}

build-zsh() {
  mkdir -p $DEPS_DIR/_zsh
  pushd $DEPS_DIR/_zsh

  # FIX for Github Actions, there's "no controlling tty", so add --with-tcsetpgrp
  # https://www.linuxfromscratch.org/blfs/view/7.5/postlfs/zsh.html

  # This builds config.modules
  $TAR_DIR/zsh-5.1.1/configure --disable-dynamic --with-tcsetpgrp

  # Build a static version of ZSH

  # For some reason the regex module isn't included if we --disable-dynamic?
  # name=zsh/regex modfile=Src/Modules/regex.mdd link=no
  # ->
  # name=zsh/regex modfile=Src/Modules/regex.mdd link=static

  # INSTALL says I need this after editing config.modules.
  sed -i 's/regex.mdd link=no/regex.mdd link=static/' config.modules
  make prep

  make

  # This way works on a given machine, but the binaries can't be relocated!
  #./configure --prefix $prefix
  #make
  #make install
  popd
}

# bash/dash: ./configure; make
# mksh: sh Build.sh
# busybox: make defconfig (default config); make

build-bash() {
  mkdir -p $DEPS_DIR/_bash
  pushd $DEPS_DIR/_bash
  $TAR_DIR/$BASH_NAME/configure
  make
  popd
}

build-dash() {
  mkdir -p $DEPS_DIR/_dash
  pushd $DEPS_DIR/_dash

  $TAR_DIR/$DASH_NAME/configure
  make
  popd
}

build-mksh() {
  mkdir -p $DEPS_DIR/_mksh
  pushd $DEPS_DIR/_mksh

  sh $TAR_DIR/mksh-R52c/Build.sh

  popd
}

build-busybox() {
  mkdir -p $DEPS_DIR/_busybox
  pushd $DEPS_DIR/_busybox

  # Out of tree instructions from INSTALL
  make KBUILD_SRC=$TAR_DIR/$BUSYBOX_NAME -f $TAR_DIR/$BUSYBOX_NAME/Makefile defconfig
  make

  popd
}

build-yash() {
  # yash isn't written with autotools or cmake
  # It seems like it has to be configured and built in the same dir.

  pushd $TAR_DIR/$YASH_NAME

  # 9/2021: Somehow hit this on my VirtualBox VM
  # The terminfo (curses) library is unavailable!
  # Add the "--disable-lineedit" option and try again.
  ./configure --disable-lineedit --prefix=$DEPS_DIR/_yash
  make
  make install

  popd
}

build-all() {
  build-bash
  build-dash
  build-mksh
  build-busybox
  build-yash

  # ZSH is a bit special
  build-zsh
}

copy-all() {
  pushd $DEPS_DIR
  cp -f -v _bash/bash .
  cp -f -v _dash/src/dash .
  cp -f -v _mksh/mksh .
  cp -f -v _busybox/busybox .
  cp -f -v _yash/bin/yash .

  ln -s -f -v busybox ash

  # In its own tree
  #ln -s -f -v zsh-out/bin/zsh .

  # Static binary
  cp -f -v _zsh/Src/zsh .
  popd
}

test-all() {
  for sh in bash dash zsh mksh ash yash; do
    $DEPS_DIR/$sh -c 'echo "Hello from $0"'

    # bash and zsh depend on libtinfo, but others don't
    # ash and zsh depend on libm, but others don't
    # bash and zsh depend on libdl, but others don't
    ldd $DEPS_DIR/$sh
  done
}

# 
# NOTE: This is older stuff I saved.  We may want to use newer shell versions?
#

_wget() {
  wget --no-clobber --directory $TAR_DIR "$@"
}

download-original-source() {
  # Note: downloading from oilshell.org/blob/spec-bin also uses this dir
  mkdir -p $TAR_DIR

  # https://tiswww.case.edu/php/chet/bash/bashtop.html - 9/2016 release
  # https://ftp.gnu.org/gnu/bash/
  _wget https://ftp.gnu.org/gnu/bash/bash-5.2.tar.gz

  # https://www.mirbsd.org/mksh.htm
  _wget https://www.mirbsd.org/MirOS/dist/mir/mksh/mksh-R59.tgz

  # https://tracker.debian.org/pkg/dash  -- old versions
  # http://www.linuxfromscratch.org/blfs/view/svn/postlfs/dash.html
  _wget http://gondor.apana.org.au/~herbert/dash/files/dash-0.5.10.2.tar.gz

  # http://zsh.sourceforge.net/News/ - 12/2016 release
  _wget https://downloads.sourceforge.net/project/zsh/zsh/5.8.1/zsh-5.8.1.tar.xz

  _wget https://osdn.net/dl/yash/yash-2.49.tar.xz

  _wget https://www.busybox.net/downloads/busybox-1.35.0.tar.bz2
}

publish-mirror() {
  ### Mirror the source tarballs at oilshell.org/blob/spec-bin
  local user=$1
  local file=$2

  local dest=$user@oilshell.org:oilshell.org/blob/spec-bin

  scp $file $dest
}

all-steps() {
  if test -d $DEPS_DIR; then
    echo "$DEPS_DIR exists: skipping build of shells"
  else
    download     # Get the right version of every tarball
    extract-all  # Extract source
    build-all    # Compile
    copy-all     # Put them in ../oil_DEPS/spec-bin
    test-all     # Run a small smoke test
  fi
}

run-task "$@"
