#!/usr/bin/env bash
#
# I think this is a zsh feature ported to bash.
#
# zsh gives /proc/self/fd/12, while bash gives /dev/fd/63
#
# Usage:
#   demo/process-sub.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

stdout() {
  cat <(seq 2) <(seq 3) 

  echo ---
  # Is it possible to pick up this failure?
  # Nope it gets lost
  cat <(seq 2) <(seq ZZ)

  echo ---
  echo pipestatus=${PIPESTATUS[@]}
}

stdin() {
  # this one hangs a little in bash
  seq 3 > >(tac)
}

stdin-shell() {
  # key difference: the SHELL ITSELF is writing to the pipe, not a forked
  # process like 'seq'

  echo $'1\n2\n3\n' > >(tac)
}

stdin-shell-2() {
  #{ echo 4; echo 5; echo 6; } > >(tac)

  echo "pid = $$"

  echo '__ ONE ___'
  echo 99 > >(tac)

  # This used to hang!
  echo '__ ONE ___'
  { echo 99; } > >(tac)

  echo '__ TWO ___'
  { echo 4; echo 5; } > >(tac)
}

both() {
  diff -u <(seq 2) <(seq 3) > >(tac) || true

  if test -n "${OIL_VERSION:-}"; then
    echo status=${_process_sub_status[@]}
  fi

  diff -u <(seq 2; exit 2) <(seq 3; exit 3) > >(tac; exit 5) || true

  if test -n "${OIL_VERSION:-}"; then
    echo status=${_process_sub_status[@]}
  fi
}


"$@"
