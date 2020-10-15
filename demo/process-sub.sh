#!/bin/bash
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

  #return

  # HANG HERE!
  # Hm I think the sentence messes it up...

  # Sequence of events:
  # when do we evaluate the redirect word?
  # Hm PopRedirects() should close the pipe to tac that we open() as
  # /dev/fd/64, and THEN later we wait()?   So I don't see a problem.

  echo '__ ONE ___'
  { echo 99; } > >(tac)

  return

  echo '__ TWO ___'
  { echo 4; echo 5; } > >(tac)
}


"$@"
