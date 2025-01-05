#!/usr/bin/env bash
#
# What happens if various build features aren't detected?
# In Python and C++
#
# Usage:
#   test/configure-effects.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# bugs:
# echo | tr
# echo | cat
# history | less

prepare-cpp() {
  ./NINJA-config.sh

  # This overwrites the config
  ./configure --without-readline --without-libc-features --without-systemtap-sdt

  ninja
}

prepare-py() {
  make
}

test-osh() {
  local osh=$1

  $osh -x -c 'set -o vi'
  $osh -x -c 'set -o emacs'

  # GLOB_PERIOD
  $osh -x -c 'shopt -s dotglob'

  # FNM_EXTMATCH
  # Hm this will works
  $osh -x -c 'echo */@(*.bash|*.asdl)'

  # HAVE_PWENT
  $osh -x -c 'compgen -A user'
}

cpp() {
  #prepare

  test-osh _bin/cxx-asan/osh
}

py() {
  #prepare-py

  ln -s -f -v oil.ovm _bin/osh

  test-osh _bin/osh
}

"$@"
