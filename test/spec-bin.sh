#!/usr/bin/env bash
#
# Build binaries for the spec tests.  This is necessary because they tickle
# behavior in minor versions of each shell.
#
# Usage:
#   ./spec-bin.sh <function name>
#
# Instructions:
#   test/spec-bin.sh download     # Get the right version of every tarball
#   test/spec-bin.sh extract-all  # Extract source
#   test/spec-bin.sh build-all    # Compile
#   test/spec-bin.sh copy-all     # Put them in _tmp/spec-bin
#   test/spec-bin.sh test-all     # Run a small smoke test
#
# Once you've run all steps manually and understand how they work, run them
# all at once with:
#
#   test/spec-bin.sh all-steps

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly DIR=$THIS_DIR/../_deps/spec-bin

readonly BUSYBOX_NAME='busybox-1.31.1'
readonly DASH_NAME='dash-0.5.10.2'
readonly YASH_NAME='yash-2.49'

# The authoritative versions!
download() {
  mkdir -p $DIR
  wget --no-clobber --directory $DIR \
    https://www.oilshell.org/blob/spec-bin/bash-4.4.tar.gz \
    https://www.oilshell.org/blob/spec-bin/$BUSYBOX_NAME.tar.bz2 \
    https://www.oilshell.org/blob/spec-bin/$DASH_NAME.tar.gz \
    https://www.oilshell.org/blob/spec-bin/mksh-R52c.tgz \
    https://www.oilshell.org/blob/spec-bin/zsh-5.1.1.tar.xz \
    https://www.oilshell.org/blob/spec-bin/$YASH_NAME.tar.xz
}

extract-all() {
  pushd $DIR

  # Remove name collision: _deps/spec-bin/mksh could be a FILE and a DIRECTORY.
  # This is unfortunately how their tarball is laid out.
  rm --verbose -r -f $DIR/mksh $DIR/mksh-R52c

  for archive in *.tar.* *.tgz; do
    echo $archive
    tar --extract --file $archive
  done
  mv --verbose --no-target-directory mksh mksh-R52c  # so it doesn't collide
  popd
}

build-zsh() {
  local prefix=$DIR/zsh-out
  pushd $DIR/zsh-5.1.1

  # This builds config.modules
  ./configure --disable-dynamic

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
  pushd $DIR/bash-4.4
  ./configure
  make
  popd
}

build-dash() {
  pushd $DIR/$DASH_NAME
  ./configure
  make
  popd
}

build-mksh() {
  pushd $DIR/mksh-R52c
  sh Build.sh
  popd
}

build-busybox() {
  pushd $DIR/$BUSYBOX_NAME
  make defconfig
  make
  popd
}

build-yash() {
  pushd $DIR/$YASH_NAME
  ./configure
  make
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
  pushd $DIR
  cp -f -v bash-4.4/bash .
  cp -f -v $DASH_NAME/src/dash .
  cp -f -v mksh-R52c/mksh .
  cp -f -v $BUSYBOX_NAME/busybox .
  cp -f -v $YASH_NAME/yash .

  ln -s -f -v busybox ash

  # In its own tree
  #ln -s -f -v zsh-out/bin/zsh .

  # Static binary
  cp -f -v zsh-5.1.1/Src/zsh .
  popd
}

test-all() {
  for sh in bash dash zsh mksh ash yash; do
    $DIR/$sh -c 'echo "Hello from $0"'

    # bash and zsh depend on libtinfo, but others don't
    # ash and zsh depend on libm, but others don't
    # bash and zsh depend on libdl, but others don't
    ldd $DIR/$sh
  done
}

# 
# NOTE: This is older stuff I saved.  We may want to use newer shell versions?
#

_wget() {
  wget --no-clobber --directory _tmp/src "$@"
}

download-original-source() {
  mkdir -p _tmp/src

  # https://tiswww.case.edu/php/chet/bash/bashtop.html - 9/2016 release
  # https://ftp.gnu.org/gnu/bash/
  _wget https://ftp.gnu.org/gnu/bash/bash-4.4.tar.gz

  # https://www.mirbsd.org/mksh.htm - no dates given
  _wget https://www.mirbsd.org/MirOS/dist/mir/mksh/mksh-R54.tgz

  # https://tracker.debian.org/pkg/dash  -- old versions
  # http://www.linuxfromscratch.org/blfs/view/svn/postlfs/dash.html
  _wget http://gondor.apana.org.au/~herbert/dash/files/dash-0.5.10.2.tar.gz

  # http://zsh.sourceforge.net/News/ - 12/2016 release
  _wget https://downloads.sourceforge.net/project/zsh/zsh/5.3.1/zsh-5.3.1.tar.xz

  _wget https://osdn.net/dl/yash/yash-2.49.tar.xz
}

publish-mirror() {
  ### Mirror the source tarballs at oilshell.org/blob/spec-bin
  local user=$1
  local host=$user.org

  local file=$2

  local dest=$user@$host:oilshell.org/blob/spec-bin

  scp $file $dest
}

publish-tmp() {
  local name=$1  # required

  local dest=oilshell.org/share/2018-10-06-tmp/
  ssh ${name}@${name}.org mkdir -p $dest
  scp _deps/re2c-1.0.3/re2c ${name}@${name}.org:$dest
}

all-steps() {
  # Uncomment to rebuild the Travis cache in _deps/
  #if false; then
  if test -d $DIR; then
    echo "$DIR exists: skipping build of shells"
  else
    download     # Get the right version of every tarball
    extract-all  # Extract source
    build-all    # Compile
    copy-all     # Put them in _tmp/spec-bin
    test-all     # Run a small smoke test
  fi
}

"$@"
