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

make-rootfs() {
  local branch='v3.22' 

  sudo ../../alpinelinux/alpine-make-rootfs/alpine-make-rootfs \
    --branch $branch \
    _chroot/alpine-$branch.tar.gz
}

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
  # buildah config --env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin $CONTAINER

  # Set some basic container metadata (optional but recommended)
  buildah config --workingdir /home/oils $CONTAINER
  buildah config --cmd /bin/sh $CONTAINER

  # Create the /app/data directory in the container
  #buildah run $CONTAINER -- mkdir -p /home/oils

  # Commit the container to create an image
  IMAGE_NAME='aports-build:latest'
  echo "Committing container to image: $IMAGE_NAME"
  buildah commit $CONTAINER $IMAGE_NAME

  # Clean up the working container
  buildah rm $CONTAINER

  echo "Image built successfully: $IMAGE_NAME"
}

list() {
  podman images | grep aports-build
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

  time podman run --rm -it \
    -v "$PWD/_tmp/mnt/data:/app/data:Z" \
    aports-build:latest \
    sh -c 'echo hi; whoami; pwd; ls -l /; ls -l /app/data'
}

task-five "$@"
