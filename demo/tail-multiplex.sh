#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o errexit

print-output() {
  local begin=${1:-1}
  local end=${2:-10}

  for i in $(seq $begin $end); do
    echo $i
    sleep 0.1
  done
}

parallel() {
  print-output 1 10 &
  print-output 11 20 &
  wait
  wait
  echo done
}

parallel2() {
  mkdir -p _tmp
  print-output 1 10 >_tmp/d1 &
  print-output 11 20 >_tmp/d2 &

  # Hm the output is not good because it prints too much
  # also --pid would be nice for stopping
  #tail -q -f _tmp/d1 _tmp/d2

  multitail _tmp/d1 _tmp/d2

  wait
  wait
  echo done
}

# TODO: try this
# https://www.vanheusden.com/multitail/

"$@"
