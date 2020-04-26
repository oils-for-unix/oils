#!/bin/bash
#
# Usage:
#   ./rr.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

download() {
  wget --directory _deps \
    https://github.com/mozilla/rr/releases/download/5.3.0/rr-5.3.0-Linux-$(uname -m).deb
}

install() {
  sudo dpkg -i _deps/rr-5.3.0-Linux-$(uname -m).deb
}

demo() {
  rr record _bin/osh_eval.dbg -c 'x=Y; echo "_$x"'
}

# rr needs /proc/sys/kernel/perf_event_paranoid <= 1, but it is 3.

# https://github.com/mozilla/rr/wiki/Building-And-Installing#os-configuration

show() {
  cat /proc/sys/kernel/perf_event_paranoid
}

allow-perf-events() {
  sudo sysctl kernel.perf_event_paranoid=1
}

"$@"
