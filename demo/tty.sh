#!/bin/bash
#
# Usage:
#   ./tty.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# makes a file called ttyrecord.  Has TIMING info.
ttyrec-demo() {
  ttyrec -e demo/pyreadline.py
}

play() {
  ttyplay ttyrecord
}

# makes a file called 'typescript'
script-demo() {
  script -c demo/pyreadline.py "$@"
}

# TODO: Can we see how efficient it is?
show-script() {
  #od -c typescript
  cat typescript
}

# Conclusion: readline is smart enough not to redraw the entire line when you
# use set_completer_delims('')!  So you should do that!
#
# You can see this by using -W -- it deletes stuff.

readonly FIFO=_tmp/script-fifo

record-to-fifo() {
  local cmd=${1:-demo/pyreadline.py}  # e.g. try zsh or bash
  mkfifo $FIFO || true
  script --flush --command "$cmd" $FIFO
}

# in another window.  This shows control codes.
# Honestly this could use a Python version using repr().

# Recording fish is interesting.  It apparently does React-like diffing.
# It optimizes the control codes when you navigate the file list.
#
# Elvish doesn't do this!  It draws the whole thing each time!

play-fifo() {
  cat -A $FIFO
}

# Cool program!
# https://github.com/haberman/vtparse
vtparse-fifo() {
  ~/git/languages/vtparse/test < $FIFO
}

"$@"
