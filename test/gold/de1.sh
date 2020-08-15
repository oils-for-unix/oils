#!/bin/bash
#
# Snippet from deboostrap.

set -e

download_debs() {
  echo download_debs
}

MIRRORS='a b'

f() {
  for m in $MIRRORS; do
    echo "m $m"
    local pkgdest="foo"
    if [ ! -e "$pkgdest" ]; then continue; fi
    pkgs_to_get="$(download_debs "$m" "$pkgdest" $pkgs_to_get 5>&1 1>&6)"
    if [ -z "$pkgs_to_get" ]; then break; fi
  done 6>&1
  echo done
}

f
