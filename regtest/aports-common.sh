# Shared between regtest/aports-*.sh

readonly CHROOT_DIR=_chroot/aports-build
readonly CHROOT_HOME_DIR=$CHROOT_DIR/home/udu

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

enter-rootfs() {
  $CHROOT_DIR/enter-bwrap.sh '' root '' "$@"
}

enter-rootfs-user() {
  enter-rootfs -u udu "$@"
  $CHROOT_DIR/enter-bwrap.sh '' udu '' "$@"
}
