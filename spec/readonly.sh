#!/bin/bash
#
# Usage:
#   ./readonly.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

f1() {
  local foo=bar
  foo=1  # can modify it now
  echo $foo

  readonly foo  # not anymore
  #foo=2  # would cause an exception

  echo done

  # This is a GLOBAL, not a local
  readonly f1_readonly=f1_readonly
}

f1

echo $f1_readonly
