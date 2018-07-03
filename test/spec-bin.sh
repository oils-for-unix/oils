#!/bin/bash
#
# Build binaries for the spec tests.
#
# Usage:
#   ./spec-bin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly DIR=_tmp/spec-bin

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

build-all() {
  # bash/dash/zsh: ./configure; make
  # mksh: sh Build.sh
  # busybox: make defconfig (default config); make

  pushd $DIR
  # TODO: Are they all different?
  popd
}

link-all() {
  pushd $DIR
  ln -s -f -v bash-4.3/bash .
  ln -s -f -v dash-0.5.8/src/dash .
  ln -s -f -v zsh-5.1.1/Src/zsh .
  ln -s -f -v mksh-R52c/mksh .
  ln -s -f -v busybox-1.22.0/busybox ./ash
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
