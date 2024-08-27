#!/usr/bin/env bash
#
# Shell functions run on the host machine, OUTSIDE the container.
#
# Usage:
#   soil/host-shim.sh <function name>
#
# Examples:
#   soil/host-shim.sh local-test-uke cpp-spec

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source soil/common.sh
source test/tsv-lib.sh

live-image-tag() {
  ### image ID -> Docker tag name
  local image_id=$1

  case $image_id in
    (app-tests)
      # rebuild with curl
      echo 'v-2023-10-05'
      ;;
    (wild)
      # rebuild with ca-certificates
      echo 'v-2024-08-26'
      ;;
    (bloaty)
      # rebuild with ca-certificates
      echo 'v-2024-08-26'
      ;;
    (benchmarks)
      # freshen up
      echo 'v-2023-07-15'
      ;;
    (benchmarks2)
      # debian 12, python3, new R-libs, cmark
      # new uftrace version
      echo 'v-2024-06-09'
      ;;
    (cpp-spec)
      # Rebuild with jq, procps
      echo 'v-2023-07-17'
      ;;
    (pea)
      # freshen up
      echo 'v-2024-06-08'
      ;;
    (cpp-small)
      # Rebuild with Docker, remove dead code
      echo 'v-2023-07-15'
      ;;
    (clang)
      # Rebuild with wedges
      echo 'v-2023-08-09'
      ;;
    (ovm-tarball)
      # bash 5.2.21
      echo 'v-2024-06-09b'
      ;;
    (other-tests)
      # freshen up
      echo 'v-2023-07-15'
      ;;
    (dummy)
      # freshen up
      echo 'v-2024-06-08'
      ;;
    (dev-minimal)
      # Use python3 wedge and mypy-0.780 repo
      echo 'v-2023-07-15'
      ;;

    # Not run directly
    (common)
      # Rebuild with wedges
      echo 'v-2023-02-28f'
      ;;
    (*)
      die "Invalid image $image"
      ;;
  esac
}

make-soil-dir() {
  log-context 'make-soil-dir'

  mkdir --verbose -p _tmp/soil
  ls -l -d . _tmp _tmp/soil

  # Match what mount-perms does
  chmod --changes 777 _tmp _tmp/soil
  ls -l -d . _tmp _tmp/soil
}

show-disk-info() {
  # Debug 'no space left on device' issue
  echo 'DISKS'
  df -h
  echo

  # Useful but many permissions errors
  if false; then
    echo 'SPACE FOR IMAGES?'
    du --si -s ~/.local/share/ || true
    echo
  fi
}

podman-prune() {
  ### Should this work on Debian?

  if ! command -v podman; then
    echo 'no podman'
    return
  fi

  echo 'IMAGES'
  podman images --all
  echo

  if false; then
    # This causes an interactive prompt
    echo 'PRUNE'
    podman system prune || true
    echo

    show-disk-info

    echo 'PRUNE AS ROOT'
    sudo podman system prune || true
    echo

    show-disk-info
  fi
}

mount-perms() {
  ### Ensure that the guest can write to bind mount

  local repo_root=$1

  #show-disk-info

  log-context 'mount-perms'

  # We have to chmod all dirs because 'build/py.sh all' creates
  # build/temp.linux-*, for example.  Also can't exclude .git/ because
  # submodules need it.
  time find "$repo_root" -type d -a -print \
    | xargs -d $'\n' -- chmod --changes 777 \
    | wc -l
  echo
}

job-reset() {
  ### Called between jobs

  #show-disk-info

  log-context 'job-reset'

  # The VM runs as the 'build' user on sourcehut.  The podman container runs as
  # 'uke' user, which apparently gets UID 100999.
  #
  # Running as 'build', we can't remove files created by the guest, so use
  # 'sudo'.
  #
  # It's really these three dirs.
  # ls -l -d _tmp/soil _tmp/soil/logs _devbuild/bin || true

  sudo $0 mount-perms $PWD
  echo

  git status .
  echo

  # Similar to functions in 'build/clean.sh'
  local -a dirs=(_tmp _bin _build _devbuild _test)
  #local -a dirs=(_tmp)

  log 'Removing temp dirs'
  log ''

  du --si -s "${dirs[@]}" || true
  rm -r -f "${dirs[@]}"
  echo

  show-disk-info
}

save-image-stats() {
  local soil_dir=${1:-_tmp/soil}
  local docker=${2:-docker}
  local image=${3:-oilshell/soil-dummy}
  local tag=${4:-latest}

  # TODO: write image.json with the name and tag?

  mkdir -p $soil_dir

  # NOTE: Works on my dev machine, but produces an empty table on CI?
  $docker images "$image:v-*" > $soil_dir/images-tagged.txt
  log "Wrote $soil_dir/images-tagged.txt"

  $docker history $image:$tag > $soil_dir/image-layers.txt
  log "Wrote $soil_dir/image-layers.txt"

  # NOTE: Works with docker but not podman!  podman doesn't support --format ?
  {
    # --human=0 gives us raw bytes and ISO timestamps
    # --no-trunc shows the full command line
    echo $'num_bytes\tcreated_at\tcreated_by'
    $docker history --no-trunc --human=0 --format '{{.Size}}\t{{.CreatedAt}}\t{{.CreatedBy}}' $image:$tag
  } > $soil_dir/image-layers.tsv
  log "Wrote $soil_dir/image-layers.tsv"

  # TODO: sum into image-layers.json
  # - total size
  # - earliest and layer date?

  here-schema-tsv >$soil_dir/image-layers.schema.tsv <<EOF
column_name   type
num_bytes     integer
created_at    string
created_by    string
EOF

  log "Wrote $soil_dir/image-layers.schema.tsv"
}

run-job-uke() {
  local docker=$1  # docker or podman
  local repo_root=$2
  local job_name=$3  # e.g. dev-minimal
  local debug_shell=${4:-}

  log-context 'run-job-uke'

  # Do this on the HOST because we write the pull time into it as well.  It's
  # shared between guest and host.
  make-soil-dir
  local soil_dir=$repo_root/_tmp/soil

  local -a flags=()

  local image_id=$job_name

  # Some jobs don't have their own image, and some need docker -t
  case $job_name in
    app-tests)
      # to run ble.sh tests
      flags=( -t )
      ;;
    cpp-coverage)
      image_id='clang'
      ;;
    cpp-tarball)
      image_id='cpp-small'
      ;;
    interactive)
      # to run 'interactive-osh' with job control enabled
      flags=( -t )

      # Reuse for now
      image_id='benchmarks'
      ;;
  esac

  local image="docker.io/oilshell/soil-$image_id"

  local tag=$(live-image-tag $image_id)

  local pull_status
  # Use external time command in POSIX format, so it's consistent between hosts
  set -o errexit
  command time -p -o $soil_dir/image-pull-time.txt \
    $docker pull $image:$tag
  pull_status=$?
  set +o errexit

  if test $pull_status -ne 0; then
    log "$docker pull failed with status $pull_status"

    # Save status for a check later
    mkdir -p _soil-jobs
    echo "$pull_status" > _soil-jobs/$job_name.status.txt

    # Return success
    return
  fi

  save-image-stats $soil_dir $docker $image $tag

  show-disk-info

  podman-prune

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
    args=(sh -c "cd /home/uke/oil; soil/worker.sh JOB-$job_name")
  fi

  $docker run "${flags[@]}" \
      --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
      $image:$tag \
      "${args[@]}"
}

did-all-succeed() {
  ### Check if the given jobs succeeded

  local max_status=0
  for job_name in "$@"; do
    local status
    read status unused_job_id < "_soil-jobs/$job_name.status.txt"

    echo "$job_name status: $status"
    if test $status -gt $max_status; then
      max_status=$status
    fi
  done

  log ''
  log "Exiting with max job status $max_status"

  return "$max_status"
}

local-test-uke() {
  ### Something I can run locally.  This is fast.

  # Simulate sourcehut with 'local-test-uke dummy dummy'
  local job_name=${1:-dummy}
  local job2=${2:-}
  local debug_shell=${3:-}  # add 'bash' to change it to a debug shell
  local docker=${4:-docker}

  local branch=$(git rev-parse --abbrev-ref HEAD)

  local fresh_clone=/tmp/soil-$job_name
  rm -r -f -v $fresh_clone

  local this_repo=$PWD
  git clone $this_repo $fresh_clone
  cd $fresh_clone
  git checkout $branch

  sudo $0 mount-perms $fresh_clone
  sudo $0 run-job-uke "$docker" $fresh_clone $job_name "$debug_shell"

  # Run another job in the same container, to test interactions

  if test -n "$job2"; then
    $0 job-reset
    sudo $0 run-job-uke "$docker" $fresh_clone $job2
  fi
}

local-shell() {
  local job_name=${1:-cpp}

  # no job 2
  local-test-uke $job_name '' bash
}

cleanup() {
  sudo rm -r -f -v _tmp/soil /tmp/soil-*
}

"$@"
