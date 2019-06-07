#!/bin/bash
#
# Usage:
#   ./sigwinch-bug.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# - Catalog all the "slow" syscalls?
# - read() and wait() are definitely there.
#   - And write(), but that appears to be handled at the Python level.
# - Catalog all the cases where CPython handles EINTR
#   - e.g. sys.stdout.write() ?
#   - see demo/cpython-signals.sh

# More test cases:
# https://github.com/oilshell/oil/wiki/Testing-the-Interactive-Shell


# Can also use the app bundle
OSH=bin/osh
#OSH=osh


# BUG: Try resizing terminal here.
# Different bug: OSH requires you to hit Ctrl-C then ENTER when running this?
case-read() {
  $OSH -i -c 'read'
}

# BUG: Try resizing terminal here.
case-read-n() {
  $OSH -i -c 'read -n 5'
}

# BUG: Try resizing terminal here.
# Hm not reproducible with $OSH -i?  Have to do it at the prompt?
# I guess this has to do with GNU readline?
pipeline() {
  $OSH -i -c 'sleep 5 | wc -l'
}

# BUG: Try resizing terminal here.
command-sub() {
  $OSH -i -c 'echo $(sleep 5; echo hi)'
}

# There is no bug, so it appears sys.stdout.write() handle EINTR?  It's a
# higher-level interface than posix.read().
write() {

  # The shell will be blocked on a write.
  $OSH -i -c 'for i in {1..1000}; do echo "[$i]"; done | sleep 5;'
}

"$@"
