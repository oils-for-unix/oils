#!/bin/bash
#
# Run spec tests on the RELEASE BINARY inside an Alpine chroot.
# This is what happens when Alpine distro maintainers build and test Oil.
#
# Based on test/alpine.sh, which just builds Oil inside Alpine.
#
# Usage:
#   test/alpine2.sh <function name>
#
# To make a spec test env:
#
#   $0 download
#   $0 extract
#   $0 setup-dns
#   $0 add-oil-build-deps

#   $0 make-oil-spec
#   $0 copy-oil-spec
#
#   test/alpine.sh interactive _chroot/spec-alpine  # enter it
#
# TODO: Fold all this into test/alpine.sh

set -o nounset
set -o pipefail
set -o errexit

readonly ROOTFS_URL='http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/alpine-minirootfs-3.11.3-x86_64.tar.gz'
readonly CHROOT_DIR=_chroot/spec-alpine

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

# So we can download packages
setup-dns() {
  test/alpine.sh setup-dns $CHROOT_DIR
}

# bash, make, gcc, musl-dev: to compile Oil
# python2, gawk: to run spec tests
#
# What about xargs?  It uses --verbose, which busybox doesn't have.
# I think I should run a minimal serial test runner, in Python maybe?

# 3/6/2020: 154 MiB
add-oil-build-deps() {
  local chroot_dir=${1:-$CHROOT_DIR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev python2 gawk
EOF
}

# TODO: Allow copying arbitrary tar, not just the one in
# _release/oil-${OIL_VERSION}

copy-tar() {
  test/alpine.sh copy-tar $CHROOT_DIR
}

test-tar() {
  test/alpine.sh test-tar $CHROOT_DIR
}

# Spec tests
make-oil-spec() {
  # TODO: maybe get rid of doctools
  # test/spec.sh is just for reference
  # web/ dir because we want the end user to be able to see it
  find \
    benchmarks/time_.py \
    test/sh_spec.py doctools/{html_head,doc_html,__init__}.py \
    test/{common,spec-common,spec,spec-alpine,spec-runner}.sh \
    spec/ \
    web/ \
    -type f \
    | xargs tar --create > _tmp/oil-spec.tar
}

_copy-oil-spec() {
  local dest=$CHROOT_DIR/src/oil-spec
  mkdir -p $dest
  cp -v _tmp/oil-spec.tar $dest
}
copy-oil-spec() { sudo $0 _copy-oil-spec "$@"; }


"$@"
