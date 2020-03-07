#!/usr/bin/env bash
#
# Make an Alpine Linux chroot and run Oil within it.
#
# Usage:
#   test/alpine.sh <function name>
#
# Use Cases:
# - _chroot/alpine-oil-tar
#   Test if the oil tarball can be configured/compiled/installed inside a
#   minimal Linux distro.  This is tested with EACH RELEASE.
# - _chroot/alpine-oil-spec
#   Test how the spec tests run (gawk and zip deps)
# - _chroot/alpine-distro-build
#   Test if Oil can run Alpine's own package manager and scripts (not done yet)
#
# Examples:
#
# 1. To make oil-tar env:
#
#   $0 download
#   $0 extract-oil-tar
#   $0 setup-dns _chroot/alpine-oil-tar
#   $0 add-oil-tar-deps
#   $0 copy-tar
#   $0 test-tar
#
# 1. To make a spec test env:
#
#   $0 download
#   $0 extract-oil-spec
#   $0 setup-dns _chroot/alpine-oil-spec
#   $0 add-oil-spec-deps
#
#   $0 copy-tar _chroot/alpine-oil-spec  # TODO: copy arbitrary tarball
#   TODO: set up non-root user
#
#   $0 make-oil-spec
#   $0 copy-oil-spec
#
# Now enter the chroot:
#
#   test/alpine.sh interactive _chroot/alpine-oil-spec
#   bash  # if you prefer, use bash inside
#
#   cd src/
#   tar -x -z < oil-$VERSION.tar.gz
#   cd oil-$VERSION/
#   ./configure && make && sudo ./install
#
#   cd ~/src/oil-spec
#   tar -x < oil-spec.tar
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

set -o nounset
set -o pipefail
set -o errexit

readonly ROOTFS_URL='http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/alpine-minirootfs-3.11.3-x86_64.tar.gz'

readonly CHROOT_OIL_TAR=_chroot/alpine-oil-tar
readonly CHROOT_OIL_SPEC=_chroot/alpine-oil-spec
readonly CHROOT_DISTRO_BUILD=_chroot/alpine-distro-build

download() {
  wget --no-clobber --directory _tmp $ROOTFS_URL
}

_extract() {
  local dest=$1

  local tarball=_tmp/$(basename $ROOTFS_URL)

  mkdir -p $dest
  # Must be run as root
  tar --extract --gzip --verbose --directory $dest < $tarball

  du --si -s $dest
}
extract-oil-tar() { sudo $0 _extract $CHROOT_OIL_TAR; }
extract-oil-spec() { sudo $0 _extract $CHROOT_OIL_SPEC; }
extract-distro-build() { sudo $0 _extract $CHROOT_DISTRO_BUILD; }

# Without this, you can't 'su myusername'.  It won't be able to execute bash.
chmod-chroot() {
  local dest=${1:-$CHROOT_OIL_TAR}
  sudo chmod 755 $dest
}

# add DNS -- for package manager

_setup-dns() {
  local chroot_dir=$1
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
add-oil-tar-deps() {
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
  sudo chroot $chroot_dir /bin/sh <<EOF
apk update
apk add bash make gcc musl-dev 
EOF
}

# Additions:
#   python2, gawk: to run spec tests
#   zip: for publishing it

# 3/6/2020: 154 MiB
add-oil-spec-deps() {
  local chroot_dir=${1:-$CHROOT_OIL_SPEC}
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
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
  sudo rm -r -rf $chroot_dir
}

# Interactive /bin/sh.
enter-chroot() {
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
  shift
  sudo chroot $chroot_dir "$@"
}

interactive() {
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
  enter-chroot $chroot_dir /bin/sh
}

#
# oil-tar functions
#

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

_copy-tar() {
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
  local name=${2:-oil}
  local version=${3:-$OIL_VERSION}

  local dest=$chroot_dir/src
  rm -r -f $dest  # make sure it's empty
  mkdir -p $dest
  cp -v _release/$name-$version.tar.gz $dest
}
copy-tar() { sudo $0 _copy-tar "$@"; }

_test-tar() {
  local chroot_dir=${1:-$CHROOT_OIL_TAR}
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

#
# oil-spec functions
#

# Spec tests
make-oil-spec() {
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
    | xargs tar --create > _tmp/oil-spec.tar
}

_copy-oil-spec() {
  local dest=$CHROOT_OIL_SPEC/src/oil-spec
  mkdir -p $dest
  cp -v _tmp/oil-spec.tar $dest
}
copy-oil-spec() { sudo $0 _copy-oil-spec "$@"; }


copy-wwz() {
  ### Take results out of chroot

  local out=_tmp/spec-results
  mkdir -p $out
  cp -v _chroot/alpine-oil-spec/src/oil-spec/*.wwz $out
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

"$@"
