#!/usr/bin/env bash
#
# Test how long it takes to read many files

big-stream() {
  cat */*.py 
  # Python messes up here!
  #*/*/*.py
}

compare() {
  echo '=== python3'

  # Buffered I/O is much faster
  time big-stream | python3 -c '
import sys
i = 0
for line in sys.stdin:
  i += 1
print(i)
'

  echo '=== awk'
  time big-stream | awk '{ i += 1 } END { print i } '

  for sh in dash bash; do
    echo === $sh

    time big-stream | $sh -c '
i=0
while read -r line; do
  i=$(( i + 1 ))
done
echo $i
'
  done


}

"$@"

