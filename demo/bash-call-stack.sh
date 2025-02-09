#!/usr/bin/env bash
#
# Usage:
#   demo/bash-call-stack.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

print-stack() {
  local n=${#BASH_SOURCE[@]}
  for (( i = 0; i < n; ++i)); do
    echo "STACK:${BASH_SOURCE[i]}:${FUNCNAME[i]}:${BASH_LINENO[i]}"
  done
}


f() {
  echo 'hi from f'
  g
}

g() {
  echo 'hi from g'
  print-stack
}

no-error() {
  # -1 position is the bottom of the stack 
  #
  # It has has demo/bash-stack.sh:main:0
  #
  # This is tested in spec/introspect.sh

  #PS4='+ ${BASH_SOURCE[-1]}:${FUNCNAME[-1]}:${BASH_LINENO[-1]} '
  #set -x
  f
}

h() {
  echo 'hi from h'
  false
  #echo $x
}

error() {
  set -o errtrace  # needed to keep it active
  trap 'print-stack' ERR

  h
}

python() {
  cat >_tmp/callstack.py <<EOF
def f():
  print("hi from f")
  exec("g()")

def g():
  print("hi from g")
  raise RuntimeError()

f()
EOF

  echo
  echo
  set +o errexit

  # 3 frames: <module> f g
  # and quotes the code
  python2 _tmp/callstack.py

  cat >_tmp/callmain.py <<EOF
def h():
  import callstack

h()
EOF

  # 5 frames: h() imprt callstack f() g() raise
  python2 _tmp/callmain.py
}

"$@"

