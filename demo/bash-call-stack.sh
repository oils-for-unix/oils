f() {
  echo 'hi from f'
  g
}

g() {
  echo 'hi from g'
}

# -1 position is the bottom of the stack 
#
# It has has demo/bash-stack.sh:main:0
#
# This is tested in spec/introspect.sh

PS4='+ ${BASH_SOURCE[-1]}:${FUNCNAME[-1]}:${BASH_LINENO[-1]} '
set -x
f
