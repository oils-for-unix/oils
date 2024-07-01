#!/usr/bin/env bash
#
# Test how long it takes to read many files

big-stream() {
  cat */*.py 
  # Python messes up here!
  #*/*/*.py
}

slow-stream() {
  ### for testing signal handling in loop
  local secs=${1:-1}

  while read -r line; do
    sleep $secs
    echo $line
  done
}

OSH=_bin/cxx-opt/osh
YSH=_bin/cxx-opt/ysh

setup() {
  local n=${1:-1}  # how many copies

  for i in $(seq $n); do
    big-stream 
  done > $BIG_FILE

  wc -l $BIG_FILE

  ninja $OSH $YSH
}

py3-count() {
  echo '=== python3'

  # Buffered I/O is much faster
  python3 -c '
import sys
i = 0
for line in sys.stdin:
  i += 1
print(i)
'
}

awk-count() {
  echo '=== awk'
  awk '{ i += 1 } END { print i } '
}

exec-ysh-count() {
  local do_trap=${1:-}

  echo '=== ysh'

  local code='
var i = 0
for _ in <> {
  setvar i += 1
}
echo $i
'

  if test -n "$do_trap"; then
    # Register BEFORE creating pipeline
    #trap usr1-handler USR1
    code="
trap 'echo \[pid \$\$\] usr1' USR1
trap 'echo \[pid \$\$\] exit with status \$?' EXIT
echo \"hi from YSH pid \$\$\"

$code
"
  fi

  # New buffered read!
  exec $YSH -c "$code"
}

usr1-handler() {
  echo "pid $$ got usr1"
}

exec-sh-count() {
  local sh=$1
  local do_trap=${2:-}

  echo "shell pid = $$"

  echo === $sh

  local code='
i=0
while read -r line; do
  i=$(( i + 1 ))
done
echo $i
'

  if test -n "$do_trap"; then
    # Register BEFORE creating pipeline
    #trap usr1-handler USR1
    code="
trap 'echo \[pid \$\$\] usr1' USR1
trap 'echo \[pid \$\$\] exit with status \$?' EXIT
echo \"hi from $sh pid \$\$\"

$code
"
  fi
  #echo "$code"

  # need exec here for trap-demo
  exec $sh -c "$code"
}

readonly BIG_FILE=_tmp/lines.txt

compare() {
  echo '=== wc'
  time wc -l < $BIG_FILE  # warmup
  echo

  time py3-count < $BIG_FILE
  echo

  time awk-count < $BIG_FILE
  echo

  time $0 exec-ysh-count < $BIG_FILE
  echo

  for sh in dash bash $OSH; do
    # need $0 because it exec
    time $0 exec-sh-count $sh < $BIG_FILE
    echo
  done
}

sh-count-slow-trap() {
  local write_delay=${1:-0.20}
  local kill_delay=${2:-0.07}
  local -a argv=( ${@:2} )

  local len=${#argv[@]}
  #echo "len=$len"
  if test $len -eq 0; then
    echo 'argv required'
  fi

  local sh=$1

  #exec-sh-count bash T & < <(seq 100 | slow-stream)

  echo "[pid $$] Spawn stream with write delay $write_delay"

  seq 10 | slow-stream $write_delay | "${argv[@]}" &
  local pid=$!

  echo "pid of background job = $pid"
  echo 'pstree:'
  pstree -p $pid
  echo

  echo "[pid $$] Entering kill loop ($kill_delay secs)"

  while true; do
    # wait for USR1 to be registered
    sleep $kill_delay

    kill -s USR1 $pid
    local status=$?

    echo "[pid $$] kill $pid status: $status"
    if test $status -ne 0; then
      break
    fi

  done

  time wait
  echo "wait status: $?"
}

compare-trap() {
  # dash exits at the first try
  #sh-count-slow-trap dash

  # Oh interesting, mksh waits until the main loop!  Different behavior
  #sh-count-slow-trap mksh

  #sh-count-slow-trap zsh

  #sh-count-slow-trap bash

  # OSH behaves like bash/zsh, yay
  sh-count-slow-trap '' '' exec-sh-count _bin/cxx-opt/osh T

  #sh-count-slow-trap '' '' exec-ysh-count T

  return

  for sh in $YSH dash bash $OSH; do
    sh-count-with-trap $sh
    echo
    echo
  done
}

"$@"

