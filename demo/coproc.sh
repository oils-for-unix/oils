#!/usr/bin/env bash
#
# Demo of coprocesses
#
# Usage:
#   ./coproc.sh <function name>
#
# Reference:
# http://unix.stackexchange.com/questions/86270/how-do-you-use-the-command-coproc-in-bash
#
# Good observations:
#
# "In short, pipes aren't good for interacting with commands. Co-processes can
# only be used to interact with commands that don't buffer their output, or
# commands which can be told not to buffer their output; for example, by using
# stdbuf with some commands on recent GNU or FreeBSD systems.
#
# That's why expect or zpty use pseudo-terminals instead. expect is a tool
# designed for interacting with commands, and it does it well."

set -o nounset
set -o pipefail
set -o errexit

proc-tree() {
  #sleep 1 &
  echo
  pstree --ascii --arguments -p $$

  # Same result
  #pstree --ascii --arguments $BASHPID
}

readonly THIS_DIR=$(dirname $0)

read-write() {
  local read_fd=$1
  local write_fd=$2

  for i in $(seq 5); do
    echo abc $i XYZ >& $write_fd
    read var <& $read_fd
    echo $var
    sleep 0.1
  done
}

simple-demo() {
  # With this syntax, there's only a single coprocess
  coproc $THIS_DIR/coproc.py 

  proc-tree
  echo "COPROC PID: $COPROC_PID"

  # In ksh or zsh, the pipes to and from the co-process are accessed with >&p
  # and <&p.
  # But in bash, the file descriptors of the pipe from the co-process and the
  # other pipe to the co-process are returned in the $COPROC array
  # (respectively ${COPROC[0]} and ${COPROC[1]}.

  argv ${COPROC[@]}

  read-write "${COPROC[@]}"
}

multi-demo() {
  proc-tree

  coproc upper {
    $THIS_DIR/coproc.py upper
  }
  echo "upper PID: $upper_PID"

  proc-tree
  read-write "${upper[@]}"

  # Close the write end to signal we'redone
  exec {upper[1]}>&-

  echo '---'

  proc-tree

  coproc lower {
    $THIS_DIR/coproc.py lower
  }
  echo "lower PID: $lower_PID"

  proc-tree
  read-write "${lower[@]}"

  exec {lower[1]}>&-
}

"$@"
