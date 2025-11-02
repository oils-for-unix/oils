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

  pushd ../../alpinelinux/aports

  # Stable release branch like 3.22-stable
  # The branch is frqeuently patched, but I guess it just needs to match the
  # dl-cdn.alpinelinux.org URL
  # https://alpinelinux.org/releases/

  local branch='3.22-stable'
  git checkout $branch
  git log -n 1
  popd > /dev/null

  echo
  echo

  pushd ../alpine-chroot-install
  git checkout master
  git log -n 1
  popd > /dev/null
}

patch-aports() {
  local cur_dir=$PWD

  pushd ../../alpinelinux/aports

  for patch_dir in $cur_dir/regtest/patches/*; do
      local package_name
      package_name=$(basename $patch_dir)

      local apkbuild=main/$package_name/APKBUILD
      git restore $apkbuild

      for mod_file in $cur_dir/regtest/patches/$package_name/*; do
          echo
          echo "*** Processing $mod_file"

          case $mod_file in
            *.patch)
              # A patch to the source code

              # Add our patches alongside Alpine's own patches

              cp -v $mod_file main/$package_name/

              # abuild's default_prepare() applies all patches inside $srcdir,
              # but they also need to be specified in the 'source=' and
              # 'sha512sums=' lists in APKBUILD
              local patch_name=$(basename $mod_file)
              local shasum=$(sha512sum $mod_file | cut -d ' ' -f1)
              sed -i "/source='*/ a $patch_name" $apkbuild
              sed -i "/sha512sums='*/ a $shasum  $patch_name" $apkbuild
              ;;

            *.apkbuild)
              # A patch to the APKBUILD file
              set -x
              git apply $mod_file
              set +x
              ;;

            *.copy)
              # A file to copy
              cp -v $mod_file main/$package_name/
              ;;
          esac
      done
  done

  popd >/dev/null
}


# 2025-11-01, after several contributed fixes
readonly TARBALL_ID='10703'

download-oils() {
  local tarball_id=${1:-$TARBALL_ID}

  local url="https://op.oilshell.org/uuu/github-jobs/$tarball_id/cpp-tarball.wwz/_release/oils-for-unix.tar"

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

  # "branch" is one of these: https://dl-cdn.alpinelinux.org/
  # it's not the aports branch
  local branch='v3.22'
  time sudo $aci -n -d $PWD/$CHROOT_DIR -b $branch
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
  apk add alpine-sdk abuild-rootbld pigz doas bash python3 findutils readline-dev
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
  # 'main' and 'community' are two "Alpine repos" stored the 'aports' git repo
  for a_repo in main community; do
    local dest=$CHROOT_HOME_DIR/aports/$a_repo/

    sudo mkdir -p $dest
    sudo rsync --archive --verbose \
      ../../alpinelinux/aports/$a_repo/ $dest

    change-perms $dest
  done
}

_patch-yash-to-disable-tests() {
  ### disable tests that use job control, causing SIGTTOU bug

  local apkbuild=$CHROOT_HOME_DIR/aports/main/yash/APKBUILD

  # make it idempotent
  if ! grep 'FOR OILS' "$apkbuild"; then
    echo '
    check() {
      echo "=== yash tests DISABLED FOR OILS ==="
    }
    ' >> $apkbuild
  fi
}

patch-yash-to-disable-tests() {
  sudo $0 _patch-yash-to-disable-tests
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

  patch-yash-to-disable-tests

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

  # -n non-interactive
  abuild-keygen --append --install -n
  '
}

apk-manifest() {
  # 1643 files - find a subset to build

  for a_repo in main community; do
    local out=$PWD/_tmp/apk-${a_repo}-manifest.txt
    mkdir -p _tmp

    pushd $CHROOT_HOME_DIR/aports/$a_repo >/dev/null
    find . -name 'APKBUILD' -a -printf '%P\n' | sed 's,/APKBUILD$,,g' | LANG=C sort | tee $out
    popd >/dev/null
  done
  wc -l _tmp/apk-*-manifest.txt
}

build-oils() {
  enter-rootfs-user sh -c '
  cd oils-for-unix-*
  ./configure
  _build/oils.sh  # do not --skip-rebuild
  doas ./install
  '
}

save-default-config() {
  regtest/aports-run.sh save-default-config
}

create-osh-overlay() {
  # _chroot/
  #   aports-build/  # chroot image
  #   osh-as-sh.overlay/     # overlay
  #     merged/      # permanently mounted
  #     work/
  #     layer/       # has the OSH symlink

  local osh_overlay=_chroot/osh-as-sh.overlay

  mkdir -v -p $osh_overlay/{merged,work,layer}

  sudo mount \
    -t overlay \
    osh-as-sh \
    -o "lowerdir=$CHROOT_DIR,upperdir=$osh_overlay/layer,workdir=$osh_overlay/work" \
    $osh_overlay/merged

  $osh_overlay/merged/enter-chroot sh -c '
  set -x
  if ! test -f /usr/local/bin/oils-for-unix; then
    echo "Build Oils first"
    exit
  fi
  ln -s -f /usr/local/bin/oils-for-unix /bin/sh
  ln -s -f /usr/local/bin/oils-for-unix /bin/ash
  ln -s -f /usr/local/bin/oils-for-unix /bin/bash
  ' dummy0
}

# Works?
patch-overlay-with-ash() {
  local dir=_chroot/osh-as-sh.overlay
  pushd $dir/layer/bin
  sudo ln -s -f -v /usr/local/bin/oils-for-unix ash
  popd
  ls -l $dir/layer/bin
}

remove-osh-overlay() {
  local dir=_chroot/osh-as-sh.overlay
  sudo umount -l $dir/merged
  sudo rm -r -f $dir
}

remove-shard-layers() {
  sudo rm -r -f _chroot/shard*
}

create-package-dirs() {
  # _chroot/
  #   package.overlay/
  #     merged/      # mounted and unmounted each time
  #     work/
  #   package-layers/
  #     baseline/
  #       gzip/
  #       xz/
  #     osh-as-sh/
  #       gzip/
  #       xz/

  mkdir -v -p _chroot/package.overlay/{merged,work}
}

archived-distfiles() {
  local a_repo=$1  # 'main' or 'community'

  local tar=_chroot/distfiles-${a_repo}.tar
  tar --create --file $tar --directory $CHROOT_DIR/var/cache/distfiles .

  tar --list < $tar
  echo
  ls -l --si $tar
  echo
}

unpack-distfiles() {
  local a_repo=$1  # 'main' or 'community'

  local tar=_chroot/distfiles-${a_repo}.tar
  sudo tar --verbose -x --directory $CHROOT_DIR/var/cache/distfiles < $tar
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

remove-all() {
  set -x
  remove-chroot || true
  remove-osh-overlay || true
  remove-shard-layers || true
}

fetch-all() {
  local tarball_id=${1:-$TARBALL_ID}

  clone-aports
  clone-aci
  checkout-stable
  patch-aports

  download-oils "$tarball_id"
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

  # TODO: Don't need this for overlayfs
  save-default-config

  create-osh-overlay
  create-package-dirs

  # makes a host file
  apk-manifest
}

task-five "$@"
