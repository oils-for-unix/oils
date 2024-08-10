#!/usr/bin/env bash
#
# Junk drawer of repros for bugs
#
# Usage:
#   test/bugs.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# bugs:
# echo | tr
# echo | cat
# history | less

esrch-code-1() {
  local n=$1
  for i in $(seq $n); do
    echo 'echo hi | tr a-z A-Z'
    #echo 'echo hi | cat'
  done
}

esrch-code-2() {
  local n=$1
  for i in $(seq $n); do
    echo 'history | less'
  done
}

esrch-test() {
  # I think

  local osh=bin/osh

  local osh=_bin/cxx-opt/osh
  ninja $osh

  esrch-code-1 1000 | $osh -i
}

#
# Bug #1853 - trap and fork optimizations - also hit by Samuel
#

trap-1() {
  local sh=${1:-bin/osh}

  set +o errexit

  # This fails to run the trap
  $sh -x -c 'echo pid=$$; trap "echo int" INT; sleep 5'

  echo "$sh status=$?"
}

# Run with bin/ysh -x to show fork opts
trap-2() {
  local sh=${1:-bin/osh}
  set +o errexit

  # This runs it
  $sh -x -c 'echo pid=$$; trap "echo int" INT; sleep 5; echo last'

  echo "$sh status=$?"
}

spec-sig() {
  ### Run spec test outside the sh-spec framework

  local sh=${1:-bin/osh}
  local sig=${2:-int}

  SH=$sh $sh spec/testdata/builtin-trap-$sig.sh
}

spec-sig-all() {
  local sig=${1:-int}

  # they all run usr1
  # they differ with respect int - only zsh prints it, and bin/osh
  #
  # zsh prints 'int'

  for sh in bin/osh bash dash mksh zsh; do
    echo '-----'
    echo "$sh"
    echo

    spec-sig $sh $sig
  done
}

sigint-loop() {
  local sh=${1:-bin/osh}

  # Hm _bin/cxx-asan/osh behaves differently here -- it doesn't run it 5 times
  # It quits the first time.
  # bin/osh works like bash/dash/mksh/zsh - they all agree
  $sh -c 'trap "echo int" INT; for i in 1 2 3 4 5; do sleep 1; done'
}

trap-with-errexit() {
  local sh=${1:-bin/osh}

  # This can't raise
  $sh -x -c 'set -e; trap "echo false; false" INT; sleep 5'
}

two-traps-return() {
  local sh=${1:-bin/osh}

  set +o errexit

  $sh -x -c '
trap "echo int; return 44" INT
trap "echo exit; return 55" EXIT
sleep 5
'
  # bash gives 130?
  echo "$sh status=$?"
}

two-traps-exit() {
  local sh=${1:-bin/osh}

  set +o errexit

  $sh -x -c '
trap "echo int; exit 44" INT
trap "echo exit; exit 55" EXIT
sleep 5
'
  # bash gives 130?
  echo "$sh status=$?"
}

two-traps-status() {
  local sh=${1:-bin/osh}

  set +o errexit

  $sh -x -c '
trap "echo int; ( exit 44 )" INT
trap "echo exit; ( exit 55 )" EXIT
sleep 5
'
  # bash gives 130?
  echo "$sh status=$?"
}

trap-line() {
  echo outer line=$LINENO
  trap 'echo "trap line=$LINENO"' INT  # shows line 1
  sleep 5
  echo hi
}

bug-1853() {
  local sh=${1:-bin/osh}

  $sh -c 'trap "echo hi" EXIT; $(which true)'

  echo --
  # NEWLINE
  $sh -c 'trap "echo hi" EXIT; $(which true)
'

  echo --
  $sh -c 'trap "echo hi" EXIT; $(which true); echo last'
}

"$@"
