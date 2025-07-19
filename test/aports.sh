#!/usr/bin/env bash
#
# Usage:
#   test/aports.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

clone-aports() {
  local dir=../../alpinelinux

  pushd $dir

  # Took 1m 13s, at 27 MiB /ssec
  time git clone \
    git@gitlab.alpinelinux.org:alpine/aports.git || true

  popd
}

clone-aci() {
  # I FORKED this
  #
  # Because this script FUCKED UP my
  #
  # /dev dir and current directory!
  #
  # Because I did rm -rf /alpine
  #
  # TODO: send patches upstream
  # - docs
  # - code

  pushd ..

  time git clone \
    git@github.com:oils-for-unix/alpine-chroot-install || true

  pushd alpine-chroot-install
  git checkout dev-andy
  popd

  popd
}

make-chroot() {
  local aci='../alpine-chroot-install/alpine-chroot-install'

  $aci --help

  set -x

  # -n: do not mount host dirs (a feature I added)

  # WTF, it creates _chroot/aports-build/_chroot/aports-build
  # SIGH

  # Requires ABSOLUTE path

  time sudo $aci -n -d $PWD/_chroot/aports-build

  # TODO: when you run it twice, it should abort if the directory is full
}

make-user() {
  _chroot/aports-build/enter-chroot adduser -D builder
}

install-packages() {
  #_chroot/aports-build/enter-chroot -u builder sh -c 'sudo apk update; sudo apk add bash'

  #_chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'
  #return

  # Must be done as root; there is no 'sudo'
  _chroot/aports-build/enter-chroot sh -c 'apk update; apk add bash'
  _chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'

  #_chroot/aports-build/enter-chroot -u builder sh -c 'apk update; apk add bash'
}

# TODO:
# - make a regular non-root user
# - build a package with plain 'abuild'?
# - install abuild-rootbld ?
# - install buildrepo?
#
# Then 
# - install OSH as /bin/sh
# - install OSH as /bin/bash
#   - I guess you install the bash package

task-five "$@"
