#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Copied into vendor/ afterward
download-greatest() {
  wget --directory _tmp \
    https://github.com/silentbicycle/greatest/archive/v1.4.2.tar.gz
}


"$@"
