#!/usr/bin/env bash
#
# Shell functions run on the host machine, OUTSIDE the container.
#
# Usage:
#   soil/host-shim.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

run-job-uke() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local task=$3  # e.g. dev-minimal

  local -a flags=()

  if test "$task" = 'app-tests'; then
    # Hack to reuse this container for build/dev.sh all
    local image="docker.io/oilshell/soil-ovm-tarball"
    # allocate pseudo TTY, otherwise fails on opening /dev/tty 
    flags=( -t )
  else
    # docker.io is the namespace for hub.docker.com
    local image="docker.io/oilshell/soil-$task"
  fi

  local metadata_dir=$repo_root/_tmp/soil

  mkdir -v -p $metadata_dir
  #chmod -v 777 $metadata_dir

  # Use external time command in POSIX format, so it's consistent between hosts
  command time -p -o $metadata_dir/image-pull-time.txt \
    $docker pull $image

  $docker run "${flags[@]}" \
      --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
      $image \
      sh -c "cd /home/uke/oil; soil/worker.sh run-$task"
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
