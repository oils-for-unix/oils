#!/bin/bash
#
# Usage:
#   ./python-language.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://stackoverflow.com/questions/11181519/python-whats-the-difference-between-builtin-and-builtins
# Hm there was a lot of renaming that happened in Python 2 and 3.  This isn't
# the best comparison.

dump-builtins() {
  local py=$1
  $py -c '
for name in sorted(dir(__builtins__)):
  print(name)
' | sort > _tmp/$py.txt
}

# Hm Python 3 moved  sorted(), etc. out of __builtins__?
builtins() {
  dump-builtins python
  dump-builtins python3

  comm _tmp/{python,python3}.txt || true
  wc -l _tmp/{python,python3}.txt
}

"$@"
