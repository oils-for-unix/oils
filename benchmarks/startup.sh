#!/usr/bin/env bash
#
# Usage:
#   ./startup.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly TIMEFORMAT='%R'

# 3 groups:
# dash/mksh/lua/awk: < 90 syscalls
# bash/zsh/perl: 145-289 syscalls
# python -S/python3 -S/ruby: 200-800 syscalls

# This throws off absolute timing, but relative still makes sense.
# TODO: get rid of wc -l if not.

# Ubuntu inside Virtualbox on Macbook Air:
#
# dash/mksh/mawk: 1 ms
# bash/gawk/perl: 2 ms
# zsh: 3 ms
# python -S: 5 ms
# python3 -S : 13 ms
# python import: 16 ms
# app.zip / hello.ovm: 10 ms
# oil true: 46 ms
# oil echo hi: 59 ms

strace-callback() {
  strace "$@" 2>&1 | wc -l
}

time-callback() {
  time "$@" >/dev/null
}

compare() {
  local callback=${1:-strace-callback}

  # dash is the fastest: 0 ms.
  for sh in bash dash mksh zsh; do
    echo $sh
    $callback $sh -c 'echo "hi" > /dev/null'
    echo
  done

  # gawk is slower than mawk
  for awk in gawk mawk; do
    echo $awk
    $callback $awk '{ print "hi" } ' < /dev/null
    echo
  done

  if which lua; then
    echo lua
    $callback lua -e 'print "hi"'
    echo
  fi

  echo perl
  $callback perl -e 'print "hi\n"'
  echo

  # Woah 247 ms?  Ruby is slower than Python.
  if which ruby; then
    echo ruby
    $callback ruby -e 'print "hi\n"'
    echo
  fi

  # Oh almost all stats come from -S!
  for py in python python3; do
    echo $py -S
    $callback $py -S -c 'print("hi")'
    echo
  done

  for py in python python3; do
    echo $py import
    $callback $py -S -c 'import json;print("hi")'
    echo
  done

  for py in python python3; do
    echo $py import
    $callback $py -S -c 'import json;print("hi")'
    echo
  done

  echo 'Small app.zip'
  $callback python -S _tmp/app.zip
  echo

  # This is close to app.zip, a few milliseconds slower.
  echo 'hello app bundle'
  $callback _bin/hello.ovm || true
  echo

  echo 'OSH app bundle true'
  $callback _bin/true
  echo

  echo 'OSH app bundle Hello World'
  $callback _bin/osh -c 'echo hi'
  echo
}

compare-strace() {
  compare strace-callback
}

compare-time() {
  compare time-callback
}

import-stats() {
  # 152 sys calls!  More than bash needs to start up.
  echo json
  strace python -c 'import json' 2>&1 | grep json | wc -l

  echo nonexistent___
  strace python -c 'import nonexistent___' 2>&1 | grep nonexistent___ | wc -l
}

make-zip() {
  rm -r -f _tmp/app
  rm -f _tmp/app.zip

  mkdir -p _tmp/app

  cat > _tmp/app/lib1.py <<EOF
print "hi from lib1"
EOF

  cat > _tmp/app/lib2.py <<EOF
print "hi from lib2"
EOF

  cat > _tmp/app/__main__.py <<EOF
import sys
sys.path = [sys.argv[0]]
import lib1
import lib2
print "hi from zip"
EOF

  pushd _tmp/app
  zip -r ../app.zip .
  popd
}

# Can get this down to 5 ms, 593 syscalls.  Needs to be much less.
test-zip() {
  python -S _tmp/app.zip
}

# This still tries to import encodings and stuff like that.
strace-zip() {
  strace python -S _tmp/app.zip
}

"$@"
