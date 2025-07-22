#!/usr/bin/env bash
#
# Code that runs inside Alpine chroot.
#
# Usage:
#   test/aports-guest.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

my-time-tsv() {
  python3 benchmarks/time_.py \
    --tsv \
    --time-span --rusage \
    "$@"
}

my-time-tsv-test() {
  # Doesn't output to stdout
  # my-time-tsv sleep 0.5

  my-time-tsv -o /tmp/my-time sleep 0.5
  cat /tmp/my-time
}

"$@"
