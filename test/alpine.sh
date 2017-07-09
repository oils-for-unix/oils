#!/bin/bash
#
# Usage:
#   ./alpine.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly ROOTFS_URL=http://dl-cdn.alpinelinux.org/alpine/v3.6/releases/x86_64/alpine-minirootfs-3.6.2-x86_64.tar.gz
readonly CHROOT_DIR=_chroot/alpine1

download() {
  wget --no-clobber --directory _tmp $ROOTFS_URL
}

_extract() {
  local tarball=_tmp/$(basename $ROOTFS_URL)
  local dest=$CHROOT_DIR

  mkdir -p $dest
  # Must be run as root
  tar --extract --gzip --verbose --directory $dest < $tarball
}
extract() { sudo $0 _extract "$@"; }

# add DNS -- for package manager

_setup-dns() {
  cat >$CHROOT_DIR/etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
}
setup-dns() { sudo $0 _setup-dns; }

# 106 MiB as of 7/7/2017.
add-oil-build-deps() {
  sudo chroot _chroot/alpine1 /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev 
EOF
}

destroy-chroot() {
  sudo rm -r -rf $CHROOT_DIR
}

# Interactive /bin/sh.
enter-chroot() {
  sudo chroot $CHROOT_DIR "$@"
}

interactive() {
  enter-chroot /bin/sh
}

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

_copy-tar() {
  local name=${1:-oil}
  local version=${2:-$OIL_VERSION}

  local dest=$CHROOT_DIR/src
  mkdir -p $dest
  cp _release/$name-$version.tar.gz $dest
  ls -l $CHROOT_DIR/src
}
copy-tar() { sudo $0 _copy-tar "$@"; }


# TODO: tarball needs to have a root directory like oil-$VERSION/.

_test-tar() {
  local name=${1:-oil}
  local version=${2:-$OIL_VERSION}

  enter-chroot /bin/sh <<EOF
set -e
cd src
tar --extract -z < $name-$version.tar.gz
cd $name-$version
./configure
time make _bin/${name}.ovm-dbg
echo
echo "*** Running _bin/${name}.ovm-dbg"
#PYTHONVERBOSE=9 
_bin/${name}.ovm-dbg --version
./install
echo
echo "*** Running /usr/bin/osh"
/usr/bin/osh --version
EOF
}
test-tar() { sudo $0 _test-tar "$@"; }

"$@"
