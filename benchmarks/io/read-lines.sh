#!/usr/bin/env bash
#
# Test how long it takes to read many files

big-stream() {
  cat */*.py 
  # Python messes up here!
  #*/*/*.py
}

py3-count() {
  echo '=== python3'

  # Buffered I/O is much faster
  time big-stream | python3 -c '
import sys
i = 0
for line in sys.stdin:
  i += 1
print(i)
'
}

awk-count() {
  echo '=== awk'
  time big-stream | awk '{ i += 1 } END { print i } '
}

ysh-count() {
  echo '=== ysh'

  local ysh=_bin/cxx-opt/ysh
  ninja $ysh

  # New buffered read!
  time big-stream | $ysh -c '
var i = 0
for _ in <> {
  setvar i += 1
}
echo $i
  '
}

compare() {
  py3-count
  echo

  awk-count
  echo

  ysh-count 
  echo

  local osh=_bin/cxx-opt/osh
  ninja $osh

  for sh in dash bash $osh; do
    echo === $sh

    time big-stream | $sh -c '
i=0
while read -r line; do
  i=$(( i + 1 ))
done
echo $i
'
    echo
  done
}

"$@"

