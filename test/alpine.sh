#!/usr/bin/env bash
#
# Make an Alpine Linux chroot and run Oils within it.
#
# Usage:
#   test/alpine.sh <function name>
#
# Use Cases:
# - _chroot/alpine-oils-tar
#   Test if the oil tarball can be configured/compiled/installed inside a
#   minimal Linux distro.  This is tested with EACH RELEASE.
# - _chroot/alpine-oils-spec
#   Test how the spec tests run (gawk and zip deps)
# - _chroot/alpine-distro-build
#   Test if OSH can run Alpine's own package manager and scripts (not done yet)
#
# Examples:
#
# 1. To make oils-tar env:
#
#   $0 download
#   $0 extract-oils-tar
#   $0 setup-dns
#   $0 add-oils-tar-deps
#
# One of:
#   devtools/release-native.sh make-tar
#   devtools/release.sh py-tarball
#
#   $0 copy-tar
#   $0 test-tar
#
# 1. To make a spec test env:
#
#   $0 download
#   $0 extract-oils-spec
#   $0 setup-dns
#   $0 add-oils-spec-deps
#
#   $0 copy-tar _chroot/alpine-oils-spec  # TODO: copy arbitrary tarball
#   TODO: set up non-root user
#
#   $0 make-oils-spec
#   $0 copy-oils-spec
#
# Now enter the chroot:
#
#   test/alpine.sh interactive _chroot/alpine-oils-spec
#   bash  # if you prefer, use bash inside
#
#   cd src/
#   tar -x -z < oils-ref-$VERSION.tar.gz
#   cd oil-$VERSION/
#   ./configure && make && sudo ./install
#
#   cd ~/src/oils-spec
#   tar -x < oils-spec.tar
#
#   test/spec-alpine.sh all
#   test/spec-alpine.sh archive-results
#
# TODO: Automate this more with an arbitrary tarball.
#
# Now again OUTSIDE:
#
#  test/alpine.sh copy-wwz
#  test/alpine.sh publish

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

readonly ROOTFS_URL='http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/alpine-minirootfs-3.11.3-x86_64.tar.gz'
#readonly ROOTFS_URL='https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/alpine-minirootfs-3.22.1-x86_64.tar.gz'

readonly CHROOT_OILS_TAR=_chroot/alpine-oils-tar
readonly CHROOT_OILS_SPEC=_chroot/alpine-oils-spec
readonly CHROOT_DISTRO_BUILD=_chroot/alpine-distro-build

download() {
  wget --no-clobber --directory-prefix _tmp $ROOTFS_URL
}

_extract() {
  local dest=$1

  local tarball=_tmp/$(basename $ROOTFS_URL)

  mkdir -p $dest
  # Must be run as root
  tar --extract --gzip --verbose --directory $dest < $tarball

  du --si -s $dest
}

extract-oils-tar() {
  mkdir -p _chroot  # should not be owned by root
  sudo $0 _extract $CHROOT_OILS_TAR
}

extract-oils-spec() {
  mkdir -p _chroot  # should not be owned by root
  sudo $0 _extract $CHROOT_OILS_SPEC;
}

# Without this, you can't 'su myusername'.  It won't be able to execute bash.
chmod-chroot() {
  local dest=${1:-$CHROOT_OILS_TAR}
  sudo chmod 755 $dest
}

# add DNS -- for package manager

_setup-dns() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  cat >$chroot_dir/etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
}
setup-dns() { sudo $0 _setup-dns "$@"; }

#
# Deps for different chroots
#

# 106 MiB as of 7/7/2017.
add-oils-tar-deps() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc g++ musl-dev 
EOF
}

# Additions:
#   python2, gawk: to run spec tests
#   zip: for publishing it

# 3/6/2020: 154 MiB
add-oils-spec-deps() {
  local chroot_dir=${1:-$CHROOT_OILS_SPEC}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev python2 gawk zip
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
  local chroot_dir=${1:-$CHROOT_DISTRO_BUILD}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash alpine-sdk
EOF
}

#
# Admin
#

list-packages() {
  local chroot_dir=${1:-$CHROOT_DISTRO_BUILD}
  sudo chroot $chroot_dir apk info
}

destroy-chroot() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  sudo rm -r -rf $chroot_dir
}

# Interactive /bin/sh.
enter-chroot() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  shift
  sudo chroot $chroot_dir "$@"
}

interactive() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  enter-chroot $chroot_dir /bin/sh
}

#
# oils-tar functions
#

readonly OILS_VERSION=$(head -n 1 oils-version.txt)

_copy-tar() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  local name=${2:-oils-for-unix}
  local version=${3:-$OILS_VERSION}

  local dest=$chroot_dir/src
  rm -r -f $dest  # make sure it's empty
  mkdir -p $dest
  cp -v _release/$name-$version.tar.gz $dest
}

copy-tar() {
  sudo $0 _copy-tar "$@"
}

_test-tar() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  local name=${2:-oils-for-unix}
  local version=${3:-$OILS_VERSION}
  local target=_bin/${name}.ovm

  # TODO:
  # - Run soil/cpp-tarball.sh build-static
  # - Then publish this musl build!

  enter-chroot "$chroot_dir" /bin/sh -c '
set -e

name=$1
version=$2
target=$3

cd src
tar --extract -z < $name-$version.tar.gz
cd $name-$version
./configure

# Build the tar
if test $name = oils-ref; then
  time make $target
  $target --version
else
  _build/oils.sh --skip-rebuild
  _bin/cxx-opt-sh/osh --version

  build/static-oils.sh
  _bin/cxx-opt-sh/osh-static --version
fi

./install
echo
echo "*** Running osh"

osh --version
echo status=$?
echo

ldd $(which osh)

echo DONE
' dummy "$name" "$version" "$target"
}

test-tar() {
  sudo $0 _test-tar "$@"
}

copy-static() {
  local chroot_dir=${1:-$CHROOT_OILS_TAR}
  local dir=_tmp/musl-libc
  mkdir -p $dir
  cp -v \
    $CHROOT_OILS_TAR/src/oils-for-unix-$OILS_VERSION/_bin/cxx-opt-sh/oils-for-unix-static* \
    $dir
  ls -l --si $dir
}

build-static-musl() {
  copy-tar
  test-tar
  copy-static
}

#
# cpp tarball
#

copy-cpp-tar() {
  copy-tar '' oils-for-unix 
}

test-cpp-tar() {
  test-tar '' oils-for-unix 
}

#
# oils-spec functions
#

# Spec tests
make-oils-spec() {
  # TODO: maybe get rid of doctools
  # test/spec.sh is just for reference
  # web/*.css dir because we want the end user to be able to see it
  find \
    benchmarks/time_.py \
    test/sh_spec.py doctools/{html_head,doc_html,__init__}.py \
    test/{common,spec-common,spec,spec-alpine,spec-runner}.sh \
    spec/ \
    web/*.css \
    -type f \
    | xargs tar --create > _tmp/oils-spec.tar
}

_copy-oils-spec() {
  local dest=$CHROOT_OILS_SPEC/src/oils-spec
  mkdir -p $dest
  cp -v _tmp/oils-spec.tar $dest
}
copy-oils-spec() { sudo $0 _copy-oils-spec "$@"; }


copy-wwz() {
  ### Take results out of chroot

  local out=_tmp/spec-results
  mkdir -p $out
  cp -v _chroot/alpine-oils-spec/src/oils-spec/*.wwz $out
  ls -l $out
}

publish() {
  ### Publish results to oilshell.org/spec-results
  # similar to web/publish.sh

  local user=$1
  local host=$user.org

  local path=$2

  local dest='oilshell.org/spec-results'
  ssh $user@$host mkdir --verbose -p $dest
  scp $path $user@$host:$dest

  echo "Visit http://$dest/$(basename $path)/"
}

name=$(basename $0)
if test "$name" = 'alpine.sh'; then
  task-five "$@"
fi
