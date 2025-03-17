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
    # off by one adjustment seems more accurate, similar to
    # https://opensource.com/article/22/7/print-stack-trace-bash-scripts
    if false; then
      echo "STACK:${BASH_SOURCE[i]}:${FUNCNAME[i+1]:-}:${BASH_LINENO[i]}"
    else
      echo "STACK:${BASH_SOURCE[i]}:${FUNCNAME[i]}:${BASH_LINENO[i]}"
    fi
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

do-command-error() {
  echo 'hi from h'

  # Hm, in OSH this does trigger the err trap, but not in bash

  if false; then
    shopt -s failglob
    echo *.zyzyz
  fi

  # simple command error
  # false

  # pipeline error
  false | true
}

error-command() {
  ### 'false' causes errexit

  set -o errtrace  # needed to keep it active
  trap 'print-stack' ERR

  do-command-error
}

do-undefined-var() {
  echo unset
  echo $oops
}

error-undefined-var() {
  ### undefined var - no stack trace!

  # I guess you can argue this is a programming bug

  set -o errtrace  # needed to keep it active
  trap 'print-stack' ERR

  do-undefined-var
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

