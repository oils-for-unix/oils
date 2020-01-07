#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

DIR=benchmarks/javascript

# TODO:
# - Use benchmarks/time.py for this and make a table
# - Upgrade quickjs

run-all() {
  local name=$1
  shift
  set -x

  time $DIR/$name.py "$@"

  time $DIR/$name.js "$@"

  time ~/src/duktape-2.5.0/duk $DIR/$name.js "$@"
  time ~/src/languages/quickjs-2019-07-09/qjs $DIR/$name.js "$@"

  time bash $DIR/$name.sh "$@"
  time zsh $DIR/$name.sh "$@"

  # OSH under CPython: 21.5 seconds.  10x slower.
  time bin/osh $DIR/$name.sh "$@"
}

# integers is a lot harder for shell than hexstring
# searching through 1000 * 1000 = 1M.

# duktape = 89 ms 
# quickjs = 18 ms  # beats node probably because of startup time
# node = 32 ms
#
# zsh: 1.2 seconds.  bash 2.5 seconds.  So JS has a big advantage here.

squares() { run-all squares; }

# duktape = 123ms
# quickjs = 71ms
# node.js = 38ms.  Not bad although that may be startup time.
# this is searching through a loop of 16 * 16 * 16 = 4096.
#
# zsh: 150 ms, bash: 165ms.  Not as big an advantage.  But still JS is better
# for code readability.
hexstring() { run-all hexstring; }


"$@"
