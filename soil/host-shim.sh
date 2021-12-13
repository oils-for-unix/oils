#!/usr/bin/env bash
#
# Shell functions run on the host machine, OUTSIDE the container.
#
# Usage:
#   soil/host-shim.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

docker-mount-perms() {
  local repo_root=$1
  local dir=$repo_root/_tmp/soil
  mkdir -p $dir
  sudo chmod --verbose 777 $dir
  ls -l -d $dir
}

mount-perms() {
  ### Ensure that the guest can write to bind mount

  local repo_root=$1

  mkdir -p "$repo_root/_tmp/soil"

  # We have to chmod all dirs because build/dev.sh all creates
  # build/temp.linux-*, for example.  Also can't exclude .git/ because
  # submodules need it.

  time find "$repo_root" -type d -a -print \
    | xargs -d $'\n' -- chmod --verbose 777
}

run-job() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local task=$3  # e.g. dev-minimal

  # docker.io is the namespace for hub.docker.com
  local image="docker.io/oilshell/soil-$task"

  local metadata_dir=$repo_root/_tmp/soil

  mkdir -p $metadata_dir  # may not exist yet

  # Use external time command in POSIX format, so it's consistent between hosts
  command time -p -o $metadata_dir/image-pull-time.txt \
    $docker pull $image

  $docker run \
      --mount "type=bind,source=$repo_root,target=/app/oil" \
      $image \
      sh -c "cd /app/oil; soil/worker.sh run-$task"
}

# TODO: migrate all containers to /home/uke
run-job-uke() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local task=$3  # e.g. dev-minimal

  # docker.io is the namespace for hub.docker.com
  local image="docker.io/oilshell/soil-$task"

  local metadata_dir=$repo_root/_tmp/soil

  mkdir -v -p $metadata_dir
  #chmod -v 777 $metadata_dir

  # Use external time command in POSIX format, so it's consistent between hosts
  command time -p -o $metadata_dir/image-pull-time.txt \
    $docker pull $image

  $docker run \
      --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
      $image \
      sh -c "cd /home/uke/oil; soil/worker.sh run-$task"
}


local-test() {
  ### Something I can run locally.  This is fast.
  local task=${1:-dummy}

  local branch=$(git rev-parse --abbrev-ref HEAD)

  local fresh_clone=/tmp/oil
  rm -r -f -v $fresh_clone

  local this_repo=$PWD
  git clone $this_repo $fresh_clone
  cd $fresh_clone
  git checkout $branch

  sudo $0 mount-perms $fresh_clone
  sudo $0 run-job docker $fresh_clone $task
}

local-test-uke() {
  ### Something I can run locally.  This is fast.
  local task=${1:-dummy}

  local branch=$(git rev-parse --abbrev-ref HEAD)

  local fresh_clone=/tmp/oil
  rm -r -f -v $fresh_clone

  local this_repo=$PWD
  git clone $this_repo $fresh_clone
  cd $fresh_clone
  git submodule update --init --recursive
  git checkout $branch

  sudo $0 mount-perms $fresh_clone
  sudo $0 run-job-uke docker $fresh_clone $task
}

cleanup() {
  sudo rm -r -f -v _tmp/soil
  sudo rm -r -f -v /tmp/oil
}

"$@"
