# Shared between regtest/aports-*.sh

readonly CHROOT_DIR=_chroot/aports-build
readonly CHROOT_HOME_DIR=$CHROOT_DIR/home/udu
readonly OVERLAY_BASE_DIR=$(pwd)/_chroot/overlay

# For he.oils.pub
readonly BASE_DIR=_tmp/aports-build

# For localhost
readonly REPORT_DIR=_tmp/aports-report

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

enter-rootfs-user-overlayfs() {
  local artifacts="$1"
  local name="$2"
  shift 2
  if [[ -z "$1" ]]; then
    echo "need a name for overlayfs"
    exit 1
  fi
  # Where everything lands
  local upper="$OVERLAY_BASE_DIR/$name"
  # Just for the temporary representation of everything
  local merged="$OVERLAY_BASE_DIR/${name}_merged"
  # Temporary folder for underneath work of overlayfs
  local work="$OVERLAY_BASE_DIR/${name}_work"

  mkdir -p "$OVERLAY_BASE_DIR"
  for d in "$upper" "$merged" "$work"; do
    sudo rm -rf "$d"
    mkdir -p "$d"
  done
  sudo mount -t overlay overlay "-olowerdir=$CHROOT_DIR,upperdir=$upper,workdir=$work" "$merged"
  $merged/enter-chroot -u udu "$@"
  sudo umount -l "$merged"

  rsync -avu "$upper/home/udu/oils/_tmp/aports-guest" "$REPORT_DIR/"
  if false; then
    # TODO: This path is a bit much hardcoded..
    # Delete, because they require a lot of storage!
    for d in "$upper" "$merged" "$work"; do
      sudo rm -rf "$d" || true
    done
  fi

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
