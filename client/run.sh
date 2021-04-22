#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  echo mystdin | client/headless_demo.py
}

# Hm this doesn't work that well
demo-pty() {
  echo mystdin | client/headless_demo.py --to-new-pty
}


"$@"
