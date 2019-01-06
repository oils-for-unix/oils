#!/bin/bash
#
# Usage:
#   ./pyreadline.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

scrape-flags() {
  demo/scrape_flags.py "$@"
}

# Commands which have long options.  Copied from bash-copmletion.  Removed
# 'less' since its help uses the pager.
readonly LONGOPT=( awk base64 bash bc bison cat chroot cp \
    csplit cut date df diff dir du env expand fmt fold gperf \
    grep grub head irb ld ldd ln ls m4 md5sum mkdir mkfifo mknod \
    mv netstat nl nm objcopy objdump od paste pr ptx readelf rm rmdir \
    sed seq sha{,1,224,256,384,512}sum shar sort split strip sum tac tail tee \
    touch tr uname unexpand uniq units vdir wc who
)

readonly FLAG_DIR=_tmp/scraped-flags

scrape-all-flags() {
  local out=$FLAG_DIR
  mkdir -p $out

  for cmd in "${LONGOPT[@]}"; do
    echo ---
    echo $cmd
    { $cmd --help 2>&1 || true; } | scrape-flags > $out/$cmd
  done

  wc -l $out/*
}

scrape-banner() {
  # Start at the second line, and look for a line that doesn't match ' or: '
  awk '
  FNR >= 2 &&
  !($0 ~ /^$/) &&   # no empty lines
  # no start with flags
  !($0 ~ /^[[:space:]]*(-|or:|Options:|Usage:|.* options:).*/) {
    print
    exit
  }
  '
}

scrape-all-banners() {
  for cmd in "${LONGOPT[@]}"; do
    # print second line
    echo -e -n "$cmd\t"
    { $cmd --help 2>&1 || true; } | scrape-banner
  done
}

ish() {
  demo/pyreadline.py $FLAG_DIR
}

"$@"
