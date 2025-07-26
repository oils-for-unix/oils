# Shared between test/aports-*.sh

readonly CHROOT_DIR=_chroot/aports-build
readonly CHROOT_HOME_DIR=$CHROOT_DIR/home/builder

# For he.oils.pub
readonly BASE_DIR=_tmp/aports-build

# For localhost
readonly REPORT_DIR=_tmp/aports-report

concat-task-tsv() {
  local config=${1:-baseline}
  python3 devtools/tsv_concat.py \
    $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config/*.task.tsv
}
