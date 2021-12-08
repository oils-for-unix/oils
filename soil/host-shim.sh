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

run-task() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local task=$3  # e.g. dev-minimal

  # docker.io is the namespace for hub.docker.com
  local image="docker.io/oilshell/soil-$task"

  time $docker pull $image

  $docker run \
      --mount "type=bind,source=$repo_root,target=/app/oil" \
      $image \
      sh -c "cd /app/oil; soil/worker.sh run-$task"
}

"$@"
