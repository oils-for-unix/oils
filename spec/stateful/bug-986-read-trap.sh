# Demo for https://github.com/oilshell/oil/issues/986
#
# Usage:
#   $SH demo/signal-during-read.sh <function name>
#
# Example:
#   bin/osh demo/signal-during-read bash_read
#
# bash and zsh explicitly handle EINTR during the 'read' builtin, and run
# pending traps!  OSH should do this too.

# Related: demo/sigwinch-bug.sh

handler() {
  echo "SIGHUP received" >&2
}

slow() {
  for i in 1 2 3; do
    echo $i
    sleep $i
  done
}

trap handler HUP

echo "PID $$"
#echo "SHELL $SHELL"

# Note: unlike the read builtin, none of bash/dash/zsh run signal handlers
# during an interrupted read.
command_sub() {
  echo "command sub"
  echo 'a=$(slow)'
  a=$(slow)
  echo "status=$? a=$a"
  echo ---
}

# There are several different kinds of 'read', test them all

bash_read() {
  echo 'read x'
  read x
  echo
  echo "status=$? x=$x"

  echo 'read -n 3 y'
  read -n 3 y
  echo "status=$? y=$y"
  echo ---

  echo 'read -d , z'
  read -d , z
  echo "status=$? z=$z"
  echo ---

  echo 'mapfile'
  mapfile
  echo "status=$? MAPFILE=${MAPFILE[@]}"
  echo ---
}

osh_read() {
  echo 'read --line'
  read --line
  echo "status=$? _line=$_line"
  echo ---

  echo 'read --all'
  read --all
  echo "status=$? _all=$_all"
  echo ---
}

"$@"
