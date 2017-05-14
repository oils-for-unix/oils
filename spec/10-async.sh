#!/bin/bash
#
# Testing compound statements with &.

# NOTE: This has a very different process pattern under dash than bash!

#set -o nounset
#set -o pipefail
set -o errexit

sleep2() {
  echo one
  sleep 0.5
  echo two
  sleep 0.5
}

proc_tree() {
  local pid=$1

  sleep 0.1  # wait for others to start
  pstree --compact --ascii $pid
}

main() {
  # A whole AND_OR can be async
  local pid=$$

  sleep2 && echo DONE &
  proc_tree $pid  # shows forking ONE shell
  wait

  # Pipeline
  sleep2 | rev && echo DONE &
  proc_tree $pid  # shows forking TWO shells
  wait
}

main "$@"
