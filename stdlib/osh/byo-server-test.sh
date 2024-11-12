#!/usr/bin/env bash

: ${LIB_OSH=stdlib/osh}

source $LIB_OSH/two.sh  # module under test
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh
source $LIB_OSH/byo-server.sh
source $LIB_OSH/task-five.sh

no-space(){
  echo hi
}

space1 (){
  echo hi
}

space2() {
  echo hi
}

space3(){  # space
  echo hi
}

space12 () {
  echo hi
}

space23() { # space
  echo hi
}

space123 () {  # space
  echo hi
}

newline()
{
  echo hi
}

newline1 ()
{
  echo hi
}

test-bash-print-funcs() {
  local status stdout_file

  #set -x
  #_bash-print-funcs
  #set +x

  nq-redir status stdout_file \
    _bash-print-funcs

  diff -u $stdout_file - <<EOF
newline
newline1
no-space
space1
space12
space123
space2
space23
space3
test-bash-print-funcs
EOF
}

task-five "$@"
