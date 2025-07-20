#!/usr/bin/env bash
#
# Usage:
#   test/aports.sh <function name>
#
# Examples:
#   $0 clone-aports
#   $0 clone-ci
#   $0 make-chroot
#   $0 install-packages   # build packages we need
#   $0 make-user
#   $0 setup-doas
#   $0 build-packages
#
# To clean up:
#
#   _chroot/aports-build/destroy --remove
# 
# This unmounts /dev /proc /sys/ properly!

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
  _chroot/aports-build/enter-chroot adduser -D builder || true

  # put it in abuild group
  _chroot/aports-build/enter-chroot addgroup builder abuild || true

  # for sudo
  _chroot/aports-build/enter-chroot addgroup builder wheel || true

  _chroot/aports-build/enter-chroot -u builder sh -c 'whoami; echo GROUPS; groups'
}

setup-doas() {
  # Manual configuration for abuild-keygen

  #sudo cat _chroot/aports-build/etc/doas.conf
  sudo rm _chroot/aports-build/etc/doas.conf

  # no password
  _chroot/aports-build/enter-chroot sh -c 'echo "permit nopass :wheel" >> /etc/doas.conf'
}

install-packages() {
  #_chroot/aports-build/enter-chroot -u builder sh -c 'sudo apk update; sudo apk add bash'

  #_chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'
  #return

  # Must be done as root; there is no 'sudo'
  # doas: for abuild-keygen?
  _chroot/aports-build/enter-chroot sh -c 'apk update; apk add bash abuild alpine-sdk doas'

  _chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'
  #_chroot/aports-build/enter-chroot -u builder sh -c 'apk update; apk add bash'
}

copy-aports() {
  local dest=_chroot/aports-build/home/builder/aports/main/

  sudo mkdir -p $dest
  sudo rsync --archive --verbose \
    ../../alpinelinux/aports/main/ $dest

  # get uid from /home/builder
  local uid
  uid=$(stat -c '%u' _chroot/aports-build/home/builder/)
  sudo chown --verbose --recursive $uid $dest
}

abuild-conf() {
  echo  
}

keys() {
  _chroot/aports-build/enter-chroot -u builder bash -c '
  abuild-keygen -h

  file $(which abuild-keygen)
  cat $(which abuild-keygen)
  # 186 line shell script
  wc -l $(which abuild-keygen)

  #exit

  #sh -x $(which abuild-keygen) --append --install
  abuild-keygen --append --install
  '
}

build-packages() {

  # Hm says abuild -r
  # https://wiki.alpinelinux.org/wiki/Abuild_and_Helpers#Basic_usage
  #
  # But Claude gave me abuild -F deps unpack


  _chroot/aports-build/enter-chroot -u builder bash -c '
  abuild --help

  ls -l /var/cache
  ls -l /var/cache/distfiles

  #dir=aports/main/bash

  # Try building lua
  #dir=aports/main/lua5.2
  dir=aports/main/mpfr4

  ls -l $dir

  pushd $dir
  #abuild fetch #verify
  #abuild unpack
  #abuild build -r

  #abuild -F deps unpack prepare build install package

  abuild -r

  popd

  exit
  abuild-keygen -h
  newapkbuild -h
  #apkbuild-pypi -h
  buildrepo -h
  '
}

# Notes:
# - buildrepo.lua is a lua script in lua-aports
# - abuild rootbld make a chroot for each package?
#
# Then 
# - install OSH as /bin/sh
# - install OSH as /bin/bash
#   - I guess you install the bash package

task-five "$@"
