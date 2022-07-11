#!/usr/bin/env bash
#
# Shell functions run on the host machine, OUTSIDE the container.
#
# Usage:
#   soil/host-shim.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh

mount-perms() {
  ### Ensure that the guest can write to bind mount

  local repo_root=$1

  mkdir -p "$repo_root/_tmp/soil"

  # We have to chmod all dirs because build/dev.sh all creates
  # build/temp.linux-*, for example.  Also can't exclude .git/ because
  # submodules need it.

  time find "$repo_root" -type d -a -print \
    | xargs -d $'\n' -- chmod --changes 777
}

run-job-uke() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local task=$3  # e.g. dev-minimal
  local debug_shell=${4:-}

  log-context 'run-job-uke'

  local -a flags=()

  local image_id
  case $task in
    (app-tests)
      # Hack to reuse this container for build/dev.sh all
      image_id='ovm-tarball'
      # allocate pseudo TTY, otherwise fails on opening /dev/tty 
      flags=( -t )
      ;;
    (cpp-small|cpp-spec)
      image_id='cpp'
      ;;
    (cpp-coverage)
      image_id='clang'
      ;;
    (*)
      # docker.io is the namespace for hub.docker.com
      image_id=$task
      ;;
  esac

  local image="docker.io/oilshell/soil-$image_id"

  local metadata_dir=$repo_root/_tmp/soil

  mkdir -v -p $metadata_dir
  #chmod -v 777 $metadata_dir

  # Use external time command in POSIX format, so it's consistent between hosts
  command time -p -o $metadata_dir/image-pull-time.txt \
    $docker pull $image

  local -a args
  if test -n "$debug_shell"; then
    # launch interactive shell
    flags+=( -i -t )

    # So we can run GDB
    # https://stackoverflow.com/questions/35860527/warning-error-disabling-address-space-randomization-operation-not-permitted
    flags+=( --cap-add SYS_PTRACE --security-opt seccomp=unconfined )

    # can mount other tools for debugging, like clang
    #local clang_dir=~/git/oilshell/oil_DEPS/clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04
    #flags+=( --mount "type=bind,source=$clang_dir,target=/home/uke/oil_DEPS/$(basename $clang_dir)" )
    
    args=(bash)
  else
    args=(sh -c "cd /home/uke/oil; soil/worker.sh JOB-$task")
  fi

  $docker run "${flags[@]}" \
      --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
      $image \
      "${args[@]}"
}

local-test-uke() {
  ### Something I can run locally.  This is fast.
  local task=${1:-dummy}

  local branch=$(git rev-parse --abbrev-ref HEAD)

  local fresh_clone=/tmp/soil-$task
  rm -r -f -v $fresh_clone

  local this_repo=$PWD
  git clone $this_repo $fresh_clone
  cd $fresh_clone
  git submodule update --init --recursive
  git checkout $branch

  sudo $0 mount-perms $fresh_clone
  sudo $0 run-job-uke docker $fresh_clone $task
}

local-shell() {
  local task=${1:-cpp}

  # Note: this currently requires local-test-uke first.  TODO: Remove that
  # restriction.

  local repo_root=/tmp/soil-$task
  # Run bash as debug shell
  sudo $0 run-job-uke docker $repo_root $task bash
}

cleanup() {
  sudo rm -r -f -v _tmp/soil /tmp/soil-*
}

"$@"
