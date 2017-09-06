#!/bin/bash
#
# Usage:
#   ./nix.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# My simpler rewrite.
isElfSimple() {
  local path=$1  # double quotes never necessary on RHS
  local magic

  # read 4 bytes from $path, without escaping, into $magic var
  read -r -n 4 magic < "$path"

  # Return the exit code of [[
  [[ "$magic" =~ ELF ]]
}

isElfSimpleWithStdin() {
  seq 3 > /tmp/3.txt
  while read line; do
    echo $line
    isElfSimple /bin/true && echo YES
    isElfSimple $0 || echo NO
    echo
  done < /tmp/3.txt
}

"$@"
