#!/bin/bash
#
# Usage:
#   ./shebang.sh is-shell PATH

# Test if the first line ends with 'sh'.
is-shell() {
  local path=$1
  local shebang
  read shebang < $path  # read a line from the file
  shebang=${shebang// /}  # strip all whitespace on the line
  [[ $shebang == *sh ]]
}

unittest() {
  for file in bin/oil.py configure install; do
    if is-shell $file; then
      echo YES $file
    else
      echo NO $file
    fi
  done
}

"$@"

