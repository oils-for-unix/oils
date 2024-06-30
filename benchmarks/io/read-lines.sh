#!/usr/bin/env bash
#
# Test how long it takes to read many files

big-stream() {
  cat */*.py 
  # Python messes up here!
  #*/*/*.py
}

setup() {
  for i in {1..2}; do
    big-stream 
  done > $BIG_FILE

  wc -l $BIG_FILE
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

ysh-count() {
  echo '=== ysh'

  local ysh=_bin/cxx-opt/ysh
  ninja $ysh

  # New buffered read!
  $ysh -c '
var i = 0
for _ in <> {
  setvar i += 1
}
echo $i
  '
}

usr1-handler() {
  echo "pid $$ got usr1"
}

exec-sh-count() {
  local sh=$1
  local do_trap=${2:-}

  echo "pid = $$"

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
trap 'echo usr1 in \$\$' USR1

$code
"
  fi
  #echo "$code"

  # need exec here for trap-demo
  exec $sh -c "$code"
}

readonly BIG_FILE=_tmp/lines.txt

compare() {

  time wc -l < $BIG_FILE  # warmup
  echo

  time py3-count < $BIG_FILE
  echo

  time awk-count < $BIG_FILE
  echo

  time ysh-count < $BIG_FILE
  echo

  local osh=_bin/cxx-opt/osh
  ninja $osh

  for sh in dash bash $osh; do
    # need $0 because it exec
    time $0 exec-sh-count $sh < $BIG_FILE
    echo
  done
}

trap-demo() {
  exec-sh-count bash T < $BIG_FILE &
  #$0 sh-count bash T &
  #$0 sh-count dash T &

  local pid=$!
  echo "background = $pid"
  pstree -p $pid

  #wait
  #echo status=$?
  #return

  while true; do
    # wait for USR1 to be registered
    sleep 0.05

    kill -s USR1 $pid
    local status=$?

    echo status=$status
    if test $status -ne 0; then
      break
    fi

  done

  wait
  echo status=$?
}

"$@"

