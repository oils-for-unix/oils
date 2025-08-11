#!/usr/bin/env bash
#
# Usage:
#   regtest/aports-container.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

setup() {
  # for rootless?
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
  CONTAINER=$(buildah from scratch)
  echo "Container ID: $CONTAINER"

  # Add the rootfs directory contents to the container
  echo "Adding rootfs contents..."
  buildah add $CONTAINER _chroot/alpine-v3.22.tar.gz /

  # Optional: Set environment variables
  # TODO: check this path, where does it come from?
  buildah config --env PATH=$GUEST_PATH $CONTAINER

  # Set some basic container metadata (optional but recommended)
  buildah config --workingdir /home/oils $CONTAINER
  buildah config --cmd /bin/sh $CONTAINER

  # Create the /app/data directory in the container
  #buildah run $CONTAINER -- mkdir -p /home/oils

  # Commit the container to create an image
  IMAGE_NAME='aports-build:latest'
  echo "Committing container to image: $IMAGE_NAME"
  buildah commit $CONTAINER $IMAGE_NAME

  # Defaults from alpine-chroot-install
  # Can't find 'apk'?
  # What's the difference in doing this with podman run?
  buildah run $CONTAINER apk add build-base ca-certificates ssl_client alpine-sdk abuild-rootbld pigz doas

  # Clean up the working container
  buildah rm $CONTAINER

  echo "Image built successfully: $IMAGE_NAME"
}

list() {
  podman images | grep aports-build
}

remove-all() {
  # It's silly that podman/docker have a separate set of commands
  # this should just be removing files!

  podman rmi -a -f
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

  time podman run --rm -it \
    -v "$PWD/_tmp/mnt/data:/app/data:ro" \
    aports-build:latest \
    sh -c '
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
}

task-five "$@"
