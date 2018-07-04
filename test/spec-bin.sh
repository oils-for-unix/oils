#!/bin/bash
#
# Build binaries for the spec tests.
#
# TODO:
# - coreutils
# - re2c for the OSH build
#
# Usage:
#   ./spec-bin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly DIR=$THIS_DIR/../_tmp/spec-bin

download() {
  mkdir -p $DIR
  wget --no-clobber --directory $DIR \
    https://www.oilshell.org/blob/spec-bin/bash-4.3.tar.gz \
    https://www.oilshell.org/blob/spec-bin/busybox-1.22.0.tar.bz2 \
    https://www.oilshell.org/blob/spec-bin/dash-0.5.8.tar.gz \
    https://www.oilshell.org/blob/spec-bin/mksh-R52c.tgz \
    https://www.oilshell.org/blob/spec-bin/zsh-5.1.1.tar.xz
}

extract-all() {
  pushd $DIR
  for archive in *.tar.* *.tgz; do
    echo $archive
    tar --extract --file $archive
  done
  mv -v mksh mksh-R52c  # so it doesn't collide
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

build-all() {
  # bash/dash: ./configure; make
  # mksh: sh Build.sh
  # busybox: make defconfig (default config); make

  # ZSH needs special builds
  build-zsh

  pushd $DIR

  # TODO: Are they all different?
  popd
}

copy-all() {
  pushd $DIR
  cp -f -v bash-4.3/bash .
  cp -f -v dash-0.5.8/src/dash .
  cp -f -v mksh-R52c/mksh .
  cp -f -v busybox-1.22.0/busybox .
  ln -s -f -v busybox ash

  # In its own tree
  #ln -s -f -v zsh-out/bin/zsh .

  # Static binary
  cp -f -v zsh-5.1.1/Src/zsh .
  popd
}

test-all() {
  for sh in bash dash zsh mksh ash; do
    $DIR/$sh -c 'echo "Hello from $0"'

    # bash and zsh depend on libtinfo, but others don't
    # ash and zsh depend on libm, but others don't
    # bash and zsh depend on libdl, but others don't
    ldd $DIR/$sh
  done
}

"$@"
