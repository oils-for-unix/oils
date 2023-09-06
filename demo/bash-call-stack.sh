#!/usr/bin/env bash
#
# Usage:
#   demo/bash-call-stack.sh

f() {
  echo 'hi from f'
  g
}

g() {
  echo 'hi from g'

  local n=${#BASH_SOURCE[@]}
  for (( i = 0; i < n; ++i)); do
    echo "STACK:${BASH_SOURCE[i]}:${FUNCNAME[i]}:${BASH_LINENO[i]}"
  done
}

# -1 position is the bottom of the stack 
#
# It has has demo/bash-stack.sh:main:0
#
# This is tested in spec/introspect.sh

#PS4='+ ${BASH_SOURCE[-1]}:${FUNCNAME[-1]}:${BASH_LINENO[-1]} '
#set -x
f
