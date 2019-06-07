#!/bin/bash
#
# Usage:
#   ./cpython-signals.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# I get EPIPE, but I don't get KeyboardInterrupt.
# Which calls can raise KeyboardInterrupt?

# https://stackoverflow.com/questions/35571440/when-is-keyboardinterrupt-raised-in-python

print-pipe() {
  # This should fill up a pipe.
  # Can't seem to get KeyboardInterrupt
  python -c 'print "x"*100000' | sleep 1
}

write-pipe() {
  python -c 'import sys; sys.stdout.write("x"*100000)' | sleep 1
}

# The easiest way to see KeyboardInterrupt.  read and write are not symmetric?
read-stdin() {
  python -c 'import sys; sys.stdin.read()'
}

"$@"
