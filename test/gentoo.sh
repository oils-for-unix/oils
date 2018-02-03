#!/bin/bash
#
# Test building the tarball on Gentoo.  Adapted from test/alpine.sh.
#
# https://wiki.gentoo.org/wiki/Chroot
#
# Usage:
#   ./gentoo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# 188 MB -- big!
# TODO: These are http-only, and need to be verified!
readonly ROOTFS_URL='http://distfiles.gentoo.org/releases/amd64/autobuilds/20180116T214503Z/stage3-amd64-20180116T214503Z.tar.xz'
readonly CHROOT_DIR=_chroot/gentoo

readonly PORTAGE_URL='http://distfiles.gentoo.org/snapshots/portage-20180202.tar.xz'

download() {
  wget --no-clobber --directory _tmp $ROOTFS_URL
  wget --no-clobber --directory _tmp $PORTAGE_URL
}

_extract() {
  local dest=${1:-$CHROOT_DIR}

  local tarball=_tmp/$(basename $ROOTFS_URL)

  mkdir -p $dest
  # Must be run as root
  tar --extract --xz --directory $dest < $tarball
}
extract() { sudo $0 _extract "$@"; }

_extract-portage() {
  local dest=${1:-$CHROOT_DIR}
  local portage_dest=$dest/usr

  local tarball=_tmp/$(basename $PORTAGE_URL)

  # Must be run as root
  tar --extract --xz --directory $portage_dest < $tarball
}
extract-portage() { sudo $0 _extract-portage "$@"; }

# Copied from the wiki page.
_mount-dirs() {
  mount --rbind /dev $CHROOT_DIR/dev
  mount --make-rslave $CHROOT_DIR/dev
  mount -t proc /proc $CHROOT_DIR/proc
  mount --rbind /sys $CHROOT_DIR/sys
  mount --make-rslave $CHROOT_DIR/sys
  mount --rbind /tmp $CHROOT_DIR/tmp 
}
mount-dirs() { sudo $0 _mount-dirs "$@"; }

_setup-portage() {
  cp -v $CHROOT_DIR/usr/share/portage/config/make.conf.example $CHROOT_DIR/etc/portage
}
setup-portage() { sudo $0 _setup-portage "$@"; }

# From alpine:

# Don't need chmod-chroot, I guess the tarball handles it.
#
# test/alpine.sh setup-dns _chroot/gentoo
# test/alpine.sh copy-tar _chroot/gentoo
# test/alpine.sh enter-chroot _chroot/gentoo

# emerge --sync -- Ran it manually

add-oil-build-deps() {
  local chroot_dir=${1:-$CHROOT_DIR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev 
EOF
}


"$@"
