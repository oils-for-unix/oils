#!/usr/bin/env bash
#
# Make a statically linked build.  Works with GNU libc and musl libc.
#
# Usage:
#   build/static-oils.sh

set -o nounset
set -o pipefail
set -o errexit

main() {
  LDFLAGS='-static' _build/oils.sh \
    --suffix '-static' --without-readline --skip-rebuild
}

main "$@"
