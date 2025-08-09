#!/usr/bin/env bash
#
# Set up Alpine Linux chroot.  See regtest/aports.md
#
# Usage:
#   regtest/aports-setup.sh <function name>
#
# Examples:
#
#   $0 fetch-all
#   $0 prepare-all
#
# Other commands:
#   $0 remove-chroot

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

clone-aports() {
  local dir=../../alpinelinux

  mkdir -p $dir
  pushd $dir

  # Took 1m 13s, at 27 MiB /ssec
  time git clone \
    https://gitlab.alpinelinux.org/alpine/aports.git || true
    #git@gitlab.alpinelinux.org:alpine/aports.git || true

  popd
}

clone-aci() {
  # I FORKED this, because this script FUCKED UP my /dev dir and current directory!
  # Sent patches upstream

  pushd ..

  time git clone \
    git@github.com:oils-for-unix/alpine-chroot-install || true

  popd
}

checkout-stable() {
  # 2025-07-25: commit that matches he.oils.pub
  # TODO: update this to a commit from a stable release branch like 3.22-stable
  # https://alpinelinux.org/releases/
  # But note that there is no branch for 3.22.1?
  pushd ../../alpinelinux/aports
  git checkout 7b59d0c9365e4230e0527ba9de3abd28ee58875d
  git log -n 1
  popd > /dev/null

  echo
  echo

  pushd ../alpine-chroot-install
  git checkout master
  git log -n 1
  popd > /dev/null
}

download-oils() {
  local job_id=${1:-9951}  # 2025-08

  local url="https://op.oilshell.org/uuu/github-jobs/$job_id/cpp-tarball.wwz/_release/oils-for-unix.tar"

  rm -f -v _tmp/oils-for-unix.tar

  #wget --no-clobber --directory _tmp "$url"
  wget --directory _tmp "$url"
}

make-chroot() {
  local aci='../alpine-chroot-install/alpine-chroot-install'

  $aci --help

  # Notes:
  # - $aci -d requires an ABSOLUTE path.  With a relative path, it creates
  # _chroot/aports-build/_chroot/aports-build Filed bug upstream.
  # - The -n flag is a feature I added: do not mount host dirs
  # - TODO: when you run it twice, it should abort if the directory is full
  # - Takes ~8 seconds

  # default packages: build-base ca-certificates ssl_client
  #
  # This is already 267 MB, 247 K files

  mkdir -p $CHROOT_DIR  # make it with normal permissions first
  time sudo $aci -n -d $PWD/$CHROOT_DIR
}

make-user() {
  enter-rootfs adduser -D udu || true

  # put it in abuild group
  enter-rootfs addgroup udu abuild || true
  # 'wheel' is for 'sudo'
  enter-rootfs addgroup udu wheel || true

  # CHeck the state
  enter-rootfs-user sh -c 'whoami; echo GROUPS; groups'
}

setup-doas() {
  # Manual configuration for abuild-keygen

  #sudo cat _chroot/aports-build/etc/doas.conf
  sudo rm -f $CHROOT_DIR/etc/doas.conf

  # no password
  enter-rootfs sh -c 'echo "permit nopass :wheel" >> /etc/doas.conf'
}

config-chroot() {
  make-user
  setup-doas
  keygen
}

add-build-deps() {
  # Must be done as root; there is no 'sudo'

  # alpine-sdk: abuild, etc.
  # abuild-rootbld: package required for 'abuild rootbld'
  # pigz: seems like it's optionally used by abuild - should probably speed
  # things up
  # doas: for abuild-keygen
  # bash python3: for time-tsv
  # findutils: for xargs --process-slot-var
  enter-rootfs sh -c '
  apk update
  apk add alpine-sdk abuild-rootbld pigz doas bash python3 findutils
  '

  # enter-rootfs -u udu bash -c 'echo "hi from bash"'
}

change-perms() {
  # pass any number of args

  # get uid from /home/udu
  local uid
  uid=$(stat -c '%u' $CHROOT_HOME_DIR)
  sudo chown --verbose --recursive $uid "$@"
}

copy-aports() {
  local dest=$CHROOT_HOME_DIR/aports/main/

  sudo mkdir -p $dest
  sudo rsync --archive --verbose \
    ../../alpinelinux/aports/main/ $dest

  change-perms $dest
}

code-manifest() {
  # TODO: need per-file tree shaking of build/py.sh
  local -a build_py=(
    build/py.sh  # to compile time-helper

    build/common.sh
    build/dev-shell.sh
    stdlib/osh/bash-strict.sh
    stdlib/osh/byo-server.sh
    stdlib/osh/task-five.sh
    stdlib/osh/two.sh
  )
  for path in \
    benchmarks/time_.py \
    benchmarks/time-helper.c \
    regtest/aports-guest.sh \
    "${build_py[@]}"
  do
    echo "$PWD/$path" "$path"
  done
}

multi-cp() {
  ### like multi cp, but works without python2

  local dest=$1
  while read -r abs_path rel_path; do
    # -D to make dirs

    # Hack: make everything executable for now
    # I feel like this should be in 'multi cp'

    install -m 755 -v -D --no-target-directory "$abs_path" "$dest/$rel_path"

    # cp -v --parents doesn't work, because it requires a directory arg
  done
}

copy-code() {
  local dest=$CHROOT_HOME_DIR/oils
  sudo mkdir -v -p $dest

  code-manifest | sudo $0 multi-cp $dest

  change-perms $dest
}

test-time-tsv() {
  enter-rootfs-user sh -c '
  cd oils
  pwd
  whoami
  echo ---

  build/py.sh time-helper
  regtest/aports-guest.sh my-time-tsv-test
  '
}

oils-in-chroot() {
  copy-aports
  copy-code
  test-time-tsv

  copy-oils
  build-oils
}

copy-oils() {
  local dest=$CHROOT_HOME_DIR

  local tar=$PWD/_tmp/oils-for-unix.tar
  pushd $dest
  sudo tar -x < $tar
  popd

  change-perms $dest/oils-for-unix-*
}

keygen() {
  enter-rootfs-user sh -c '
  #abuild-keygen -h
  abuild-keygen --append --install
  '
}

apk-manifest() {
  # 1643 files - find a subset to build
  local out=$PWD/_tmp/apk-manifest.txt
  mkdir -p _tmp

  pushd $CHROOT_HOME_DIR/aports/main >/dev/null
  find . -name 'APKBUILD' -a -printf '%P\n' | LANG=C sort | tee $out
  popd >/dev/null
}

build-oils() {
  enter-rootfs-user sh -c '
  cd oils-for-unix-*
  ./configure
  _build/oils.sh --skip-rebuild
  doas ./install
  '
}

save-default-config() {
  regtest/aports-run.sh save-default-config
}

unpack-distfiles() {
  sudo tar --verbose -x --directory $CHROOT_DIR/var/cache/distfiles < _chroot/distfiles.tar
}

show-distfiles() {
  ls -l $CHROOT_DIR/var/cache/distfiles
}

_install-hook() {
  local bwrap=${1:-}

  local out=enter-rootfs
  ../alpine-chroot-install/alpine-chroot-install -g > $out
  chmod +x $out
  echo "Wrote $out"

  local src
  if test -n "$bwrap"; then
    hook=regtest/aports/enter-hook-bwrap.sh
  else
    hook=../alpine-chroot-install/enter-hook-chroot 
  fi

  cp -v $hook $CHROOT_DIR/enter-hook
}

install-hook() {
  sudo $0 _install-hook "$@"
}

_install-enter-bwrap() {
  # don't need this other bwrap script
  rm -f -v $CHROOT_DIR/enter-hook

  cp -v regtest/aports/enter-bwrap.sh $CHROOT_DIR
}

install-enter-bwrap() {
  sudo $0 _install-enter-bwrap "$@"
}

remove-chroot() {
  # This unmounts /dev /proc /sys/ properly!
  $CHROOT_DIR/destroy --remove
}

fetch-all() {
  clone-aports
  clone-aci
  checkout-stable
  download-oils
}

prepare-all() {
  # $0 make-chroot     # 267 MB, 247 K files
  #                    # ncdu shows gcc is big, e.g. cc1plus, cc1, lto1 are
  #                    # each 35-40 MB
  # $0 add-build-deps  # add packages that build packages
  #                    # 281 MB, 248 K files
  # $0 config-chroot   # user/groups, keygen
  # $0 oils-in-chroot  # copy-aports: 307 MB, 251 K files

  make-chroot   
  add-build-deps

  config-chroot   

  oils-in-chroot  

  save-default-config

  # makes a host file
  apk-manifest
}

task-five "$@"
