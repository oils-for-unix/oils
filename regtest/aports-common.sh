# Shared between regtest/aports-*.sh

readonly CHROOT_DIR=_chroot/aports-build
readonly CHROOT_HOME_DIR=$CHROOT_DIR/home/udu

# For he.oils.pub
readonly BASE_DIR=_tmp/aports-build

# For localhost
readonly REPORT_DIR=_tmp/aports-report

readonly INTERACTIVE="${INTERACTIVE:-}"

concat-task-tsv() {
  local config=${1:-baseline}
  python3 devtools/tsv_concat.py \
    $CHROOT_HOME_DIR/oils/_tmp/aports-guest/$config/*.task.tsv
}

enter-rootfs() {
  $CHROOT_DIR/enter-chroot "$@"
}

enter-rootfs-user() {
  enter-rootfs -u udu "$@"
}

enter-overlayfs-user() {
  local name=$1
  shift

  # output ends up in the upperdir
  #local upper="$OVERLAY_BASE_DIR/$name"
  local upper=_chroot/overlay/upper/$name

  # workdir is scratch space
  local work=_chroot/overlay/work
 # "$OVERLAY_BASE_DIR/${name}_work"

  # the unified view we chroot into
  #local merged="$OVERLAY_BASE_DIR/${name}_merged"
  local merged=_chroot/overlay/merged

  mkdir -p $upper $work $merged

  # myoverlay is the 'source'
  sudo mount \
    -t overlay \
    myoverlay \
    -o "lowerdir=$CHROOT_DIR,upperdir=$upper,workdir=$work" \
    "$merged"

  sudo mount \
    -t proc \
    "my_chroot_proc" $merged/proc

  sudo mount \
    -t sysfs \
    "my_chroot_sysfs" $merged/sys

  sudo mount \
    -t devtmpfs \
    "my_chroot_devtmpfs" $merged/dev

  $merged/enter-chroot -u udu "$@"

  unmount-loop $merged/proc
  unmount-loop $merged/sys
  unmount-loop $merged/dev
  unmount-loop $merged
}

unmount-loop() {
  local merged=$1

  # unmount it in a loop, to ensure that we can re-mount it later
  while true; do
    # Lazy umount seems necessary?  Otherwise we get 'target is busy'
    # I suppose processes started inside the chroot may still be running
    sudo umount -l "$merged"
    if ! mountpoint --quiet "$merged"; then
      break
    fi
    echo "Waiting to unmount: $merged"
    sleep 0.1
  done
}

# Note: these functions aren't used.  bwrap is problematic when the container
# has multiple UIDs.
#
# We wanted to replace chroot with bwrap, because 'abuild rootbld' uses bwrap,
# and bwrap can't be run inside a chroot.
#
# But bwrap uses mount(), which requires a new user namespace, which creates a
# host/guest UID mapping problem.
# 
# See Zulip for details

if false; then
  enter-rootfs() {
    $CHROOT_DIR/enter-bwrap.sh '' root '' "$@"
  }

  enter-rootfs-user() {
    enter-rootfs -u udu "$@"
    $CHROOT_DIR/enter-bwrap.sh '' udu '' "$@"
  }
fi
