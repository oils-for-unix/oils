#!/bin/bash
#
# Usage:
#   ./globstar.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

shopt -s globstar || true

demo() {
  local root=_tmp/globstar
  mkdir -p $root/{Python,Py}

  mkdir -p $root/Py/zz/on

  touch $root/Python/foo.py
  touch $root/Py/zz/on/bar.py

  tree $root


  echo $root/**/*.py

  # OK this is weird, ** only crosses directory boundaries when it's at the
  # end?  It doesn't exactly make sense.
  #
  # Try with zsh too.
  echo $root/Py**on/*.py

  echo "zsh version: ${ZSH_VERSION:-}"
  echo "bash version: ${BASH_VERSION:-}"
}

with-zsh() {
  zsh $0 demo
}

"$@"
