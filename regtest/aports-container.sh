#!/usr/bin/env bash
#
# Usage:
#   regtest/aports-container.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

# Flow
#
# - make-chroot
# - add-build-deps - extra packages
# - config-chroot - users/groups, keygen
# - oils-in-chroot - can this be bind mount?
# - save-default-config
#   - hm maybe we can use LAYERS here - baseline and osh
#
# - fetch-packages
#   - this can be another layer
# - build-packages, which yields TSV and logs
#   - do we use podman cp?
#   - or do we set up a bind mount, and aports-guest.sh  knows how to write
#   there?
#     - /home/udu/oils/_tmp/aports-guest could be the bind mount
#     - back to _tmp/aports-guest
#
# - and then we can push to a central registry?
#   - packages are 6 GB, so I guess we can take advantage of that
#
# TODO:
# - test abuild rootbld


deps() {
  # https://blog.abysm.org/2023/06/switching-system-wide-default-storage-driver-from-vfs-to-overlayfs-for-podman-on-debian-bookworm/

  # containers-storage needed on Debian bookworm for overlayfs

  sudo apt-get install podman containers-storage
}

system-reset() {
  # this removes everything
  podman system reset
}

system-prune() {
  # this is GC - it sorta works
  podman system prune -a
}

show-work-area() {
  # 16K files, each layer is already materialized

  # Hm the container is 277 M
  # But this work dir is 580 M , after podman system reset?
  # It's doubling the storage?
  # Because it's the VFS driver?  Geez
  # for rootless operation

  local work_dir=~/.local/share/containers/storage/ 

  set +o errexit
  find $work_dir | wc -l

  du --si -s $work_dir
}

remove-all() {
  # It's silly that podman/docker have a separate set of commands
  # this should just be removing files!

  podman rmi -a -f
}

check-kernel-module() {
  lsmod | grep overlay
}

migrate() {
  # not sure if we need this
  podman system migrate
}

readonly branch='v3.22' 
readonly ROOTFS_TAR=_chroot/alpine-$branch.tar.gz

make-rootfs() {
  rm -f -v $ROOTFS_TAR

  # apk-tools needed to bootstrap?  otherwise we can't apk add later
  sudo ../../alpinelinux/alpine-make-rootfs/alpine-make-rootfs \
    --branch $branch \
    --packages 'apk-tools' \
    $ROOTFS_TAR
}

list-tar() {
  tar --list -z < $ROOTFS_TAR
  echo

  ls -l --si $ROOTFS_TAR
}

# copied from /etc/profile in the chroot
readonly GUEST_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

make-oci() {
  ### make OCI image with buildah 
  # there is also the pure hsell 'sloci-image' from Alpine

  set -x

  # Create a new container from scratch
  echo "Creating container from rootfs..."
  c1=$(buildah from scratch)
  echo "Container ID: $c1"

  # Add the rootfs directory contents to the container
  echo "Adding rootfs contents..."
  buildah add $c1 _chroot/alpine-v3.22.tar.gz /

  # Optional: Set environment variables
  # TODO: check this path, where does it come from?
  buildah config --env PATH=$GUEST_PATH $c1

  # Set some basic container metadata (optional but recommended)
  buildah config --workingdir /home/oils $c1
  buildah config --cmd /bin/sh $c1

  # copied from regtest/aports-setup.sh
  buildah run $c1 -- adduser -D udu
  buildah run $c1 -- addgroup udu abuild
  buildah run $c1 -- addgroup udu wheel
  buildah run $c1 -- sh -c \
    'echo "permit nopass :wheel" >> /etc/doas.conf'

  buildah config --user udu $c1

  # Create the /app/data directory in the container
  #buildah run $c1 -- mkdir -p /home/oils

  # Commit the container to create an image
  IMAGE_NAME='aports-build:latest'
  echo "Committing container to image: $IMAGE_NAME"
  buildah commit $c1 $IMAGE_NAME

  # necessary for 2 layers
  local c2
  c2=$(buildah from $IMAGE_NAME)

  # Defaults from alpine-chroot-install
  buildah run --user root $c2 -- \
    apk add build-base ca-certificates ssl_client alpine-sdk abuild-rootbld pigz doas

  # Run as udu
  buildah run $c2 -- \
    abuild-keygen --append --install -n

  buildah commit $c2 $IMAGE_NAME

  # Hm this seems necessary to clean up the work area?  Why?
  # system-prune also works, but it's a bad interface!
  #
  # I don't see why buildah does this extra copying ...

  #buildah rm $c2

  echo "Image built successfully: $IMAGE_NAME c1=$c1 c2=$c2"
}


run() {
  # Run the container with podman (rootless) and bind mount a dir

  # Make sure the host directory exists
  local host_dir=_tmp/mnt/data
  mkdir -p $host_dir
  touch $host_dir/foo.txt

  # Run the container with bind mount
  # --rm: remove container when it exits
  # -it: interactive with tty
  # -v: bind mount (volume)
  #
  # takes ~213 to ~275 ms to run

  # -v accepts :ro or :rw for mount options
  # also :z :Z selinux stuff

  local script='
      echo hi
      whoami
      pwd
      ls -l /
      echo
      ls -l /app/data
      echo
      apk list

      #ping www.google.com
      nslookup google.com
      echo

      ip addr show
      echo

      #ping host.containers.internal
      #echo

      #ping www.google.com

      nc google.com 80 <<"EOF"
GET /
EOF
      '

  local script='
  #ls -l /home/udu/aports/main

  whoami
  pwd

  abuild -f -r -C ~/aports/main/lua5.4 rootbld
  '
  # --userns=keep-id for mounts
  time podman run --rm -it \
    --privileged \
    --userns=keep-id \
    -v "$PWD/_tmp/mnt/data:/app/data:ro" \
    -v "$PWD/../../alpinelinux/aports/main:/home/udu/aports/main:rw" \
    aports-build:latest \
    sh -c "$script"

}

save() {
  local tar=_tmp/aports-oci.tar 
  rm -f -v $tar
  podman save -o $tar aports-build:latest
}

extract-saved() { 
  local tar=_tmp/aports-oci.tar 

  tar --list < _tmp/aports-oci.tar 
  echo

  ls -l --si $tar

  local tmp=_tmp/aports-oci
  rm -r -f $tmp
  mkdir -p $tmp
  pushd $tmp
  tar -x < ../aports-oci.tar
  popd
}

show-saved() {
  tree -h _tmp/aports-oci
}

list() {
  podman images | grep aports-build
}

test-rootless-overlay() {
  # AH, this works with --mount!  Cool!

  unshare --user --map-root-user --mount -- bash -c '
  dir=_tmp/overlay-test
  mkdir -p $dir/{lower,upper,work,merged}
  echo "lower" > $dir/lower/foo

  # Try to mount as regular user
  #
  # permission denied
  # how does podman do it?  Test it out

  mount -t overlay overlay \
    -o lowerdir=$dir/lower,upperdir=$dir/upper,workdir=$dir/work \
    $dir/merged

  echo MERGED
  ls -l $dir/merged
  echo "modify" > $dir/merged/foo
  cat $dir/merged/foo

  tree $dir

  echo LOWER
  cat $dir/lower/foo
  echo

  echo UPPER
  cat $dir/upper/foo
  echo
  '
}

task-five "$@"
