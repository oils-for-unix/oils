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

# TODO: Add to benchmarks2, which uses the oils-for-unix
OSH_OPT=_bin/cxx-opt/osh
YSH_OPT=_bin/cxx-opt/ysh

OSH_ASAN=_bin/cxx-asan/osh
YSH_ASAN=_bin/cxx-asan/ysh

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
  local ysh=$1
  local do_trap=${2:-}

  echo '=== ysh'

  local code='
var i = 0
for _ in (stdin) {
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
  exec $ysh -c "$code"
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

compare-line-count() {
  echo '=== wc'
  time wc -l < $BIG_FILE  # warmup
  echo

  time py3-count < $BIG_FILE
  echo

  time awk-count < $BIG_FILE
  echo

  time $0 exec-ysh-count $YSH_OPT < $BIG_FILE
  echo

  for sh in dash bash $OSH_OPT; do
    # need $0 because it exec
    time $0 exec-sh-count $sh < $BIG_FILE
    echo
  done
}

sh-count-slow-trap() {
  local write_delay=${1:-0.20}
  local kill_delay=${2:-0.07}
  local -a argv=( ${@:3} )

  local len=${#argv[@]}
  #echo "len=$len"

  if test $len -eq 0; then
    echo 'argv required'
  fi
  echo "argv: ${argv[@]}"

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

test-ysh-for() {
  sh-count-slow-trap '' '' exec-ysh-count $YSH_ASAN T
  #sh-count-slow-trap '' '' exec-ysh-count bin/ysh T

  #sh-count-slow-trap 2.0 0.7 exec-ysh-count bin/ysh T

  #sh-count-slow-trap 2.0 0.7 exec-ysh-count $YSH_ASAN T
}

test-ysh-read-error() {
  ### testing errno!

  set +o errexit
  $YSH_ASAN -c 'for x in (stdin) { echo $x }' < /tmp
  echo status=$?
}

test-read-errors() {
  set +o errexit

  # Awk prints a warning, but exits 0!
  awk '{ print }' < /tmp
  echo status=$?
  echo

  seq 3 | perl -e 'while (<>) { print "-" . $_ }'

  # Hm perl doesn't report this error!
  perl -e 'while (<>) { print }' < /tmp
  echo status=$?

  echo

  python3 -c '
import sys
for line in sys.stdin:
  print(line)
print("end")
' < /tmp
  echo status=$?


}

readonly BIG_FILE=_tmp/lines.txt

setup-benchmark() {
  local n=${1:-1}  # how many copies
  mkdir -p $(dirname $BIG_FILE)

  for i in $(seq $n); do
    big-stream 
  done > $BIG_FILE

  wc -l $BIG_FILE

  ninja $OSH_OPT $YSH_OPT
}

setup-test() {
  ninja $OSH_ASAN $YSH_ASAN
}

soil-benchmark() {
  setup-benchmark

  compare-line-count
}

soil-test() {
  setup-test

  # dash exits at the first try
  #sh-count-slow-trap '' '' exec-sh-count dash T

  #sh-count-slow-trap '' '' exec-sh-count bash T

  # Oh interesting, mksh waits until the main loop!  Different behavior
  #sh-count-slow-trap '' '' exec-sh-count mksh T

  sh-count-slow-trap '' '' exec-sh-count $OSH_ASAN T

  # OSH behaves like bash/zsh, yay

  test-ysh-for


  return

  for sh in $YSH_OPT dash bash $OSH_OPT; do
    sh-count-with-trap $sh
    echo
    echo
  done
}

"$@"

