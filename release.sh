#!/bin/bash
#
# Usage:
#   ./release.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Stub for release tarball
tarball() {
  local out=_tmp/osh.tar

  # Include tests for now?  TODO: Get rid of tools.
  tar --create --gzip --file $out.gz */*.py */*.c
  tar --create --xz --file $out.xz */*.py */*.c

  ls -l $out.gz $out.xz
}

"$@"
