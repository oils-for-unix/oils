#!/bin/bash
#
# Demo of variable scope.

#set -o nounset
set -o pipefail
set -o errexit

my_global=G1

func() {
  # This makes a NEW local variable my_global.
  # Yeah I think this is amenable to static analysis.
  local loc1=L1 my_global loc2=L2

  my_global=LL
  echo "my_global in function: $my_global"

  loc1=L3
  echo "loc1: $loc1 loc2: $loc2"

  # TODO: Add declare
}

func2() {
  my_global=G2
  func2_global=G3
}

func
echo "my_global: $my_global"

func2

echo "AFTER mutation my_global: $my_global"
echo "func2_global $func2_global"

# These don't leak
echo "loc1: $loc1 loc2: $loc2"
