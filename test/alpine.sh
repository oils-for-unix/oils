#!/bin/bash
#
# Make an Alpine Linux chroot.
#
# Use Cases:
# - Test if the oil tarball can be configured/compiled/installed inside a
#   minimal Linux distro.
# - TODO: Test BUILDING this distro, by running their ash/bash scripts.
#   - Should symlink BOTH /bin/sh and /bin/bash to osh!
#
# Usage:
#   ./alpine.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly ROOTFS_URL='http://dl-cdn.alpinelinux.org/alpine/v3.6/releases/x86_64/alpine-minirootfs-3.6.2-x86_64.tar.gz'
readonly CHROOT_DIR=_chroot/alpine1

readonly DISTRO_BUILD_CHROOT_DIR=_chroot/alpine-distro-build

download() {
  wget --no-clobber --directory _tmp $ROOTFS_URL
}

_extract() {
  local dest=${1:-$CHROOT_DIR}

  local tarball=_tmp/$(basename $ROOTFS_URL)

  mkdir -p $dest
  # Must be run as root
  tar --extract --gzip --verbose --directory $dest < $tarball
}
extract() { sudo $0 _extract "$@"; }
extract-distro-build() { sudo $0 _extract $DISTRO_BUILD_CHROOT_DIR; }

# Without this, you can't 'su myusername'.  It won't be able to execute bash.
chmod-chroot() {
  local dest=${1:-$CHROOT_DIR}
  sudo chmod 755 $dest
}

# add DNS -- for package manager

_setup-dns() {
  local chroot_dir=${1:-$CHROOT_DIR}
  cat >$chroot_dir/etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
}
setup-dns() { sudo $0 _setup-dns "$@"; }

# 106 MiB as of 7/7/2017.
add-oil-build-deps() {
  local chroot_dir=${1:-$CHROOT_DIR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev 
EOF
}

# alpine-sdk scripts are /bin/sh busybox scripts!
# Executing busybox-1.26.2-r5.trigger
# Executing ca-certificates-20161130-r2.trigger
# OK: 195 MiB in 72 packages
#
# Hm they still have triggers...
# 72 packages.  bash/readline are installed!

add-alpine-sdk() {
  local chroot_dir=${1:-$DISTRO_BUILD_CHROOT_DIR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash alpine-sdk
EOF
}

list-packages() {
  local chroot_dir=${1:-$DISTRO_BUILD_CHROOT_DIR}
  sudo chroot $chroot_dir apk info
}

destroy-chroot() {
  local chroot_dir=${1:-$CHROOT_DIR}
  sudo rm -r -rf $chroot_dir
}

# Interactive /bin/sh.
enter-chroot() {
  local chroot_dir=${1:-$CHROOT_DIR}
  shift
  sudo chroot $chroot_dir "$@"
}

interactive() {
  local chroot_dir=${1:-$CHROOT_DIR}
  enter-chroot $chroot_dir /bin/sh
}

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

# TODO: Factor these out into test/chroot.sh.  You can test it in a Gentoo
# chroot too.

_copy-tar() {
  local chroot_dir=${1:-$CHROOT_DIR}
  local name=${2:-oil}
  local version=${3:-$OIL_VERSION}

  local dest=$chroot_dir/src
  mkdir -p $dest
  cp -v _release/$name-$version.tar.gz $dest
}
copy-tar() { sudo $0 _copy-tar "$@"; }

_test-tar() {
  local chroot_dir=${1:-$CHROOT_DIR}
  local name=${2:-oil}
  local version=${3:-$OIL_VERSION}

  local target=_bin/${name}.ovm
  #local target=_bin/${name}.ovm-dbg

  enter-chroot "$chroot_dir" /bin/sh <<EOF
set -e
cd src
tar --extract -z < $name-$version.tar.gz
cd $name-$version
./configure
time make $target
echo
echo "*** Running $target"
#PYTHONVERBOSE=9 
$target --version
./install
echo
echo "*** Running osh"
osh --version
echo status=$?
echo DONE
EOF
}
test-tar() { sudo $0 _test-tar "$@"; }

"$@"
