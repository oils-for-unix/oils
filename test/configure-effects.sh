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

  set +o errexit
  # HAVE_PWENT
  $osh -x -c 'compgen -A user'

  # FNM_EXTMATCH in glob()
  # Hm this will works
  $osh -x -c 'echo */*/t@(*.asdl|*.sh)'
  echo status=$?

  # FNM_EXTMATCH in fnmatch()
  $osh -x -c 'case foo.py in @(*.asdl|*.py)) echo py ;; esac'
  echo status=$?
}

cpp() {
  #prepare

  test-osh _bin/cxx-asan/osh
}

py() {
  #prepare-py

  ln -s -f -v oil.ovm _bin/osh

  #test-osh bin/osh

  test-osh _bin/osh
}

"$@"
