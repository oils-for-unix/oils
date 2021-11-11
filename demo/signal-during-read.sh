# Demo for https://github.com/oilshell/oil/issues/986
#
# bash and zsh explicitly handle EINTR during the 'read' builtin, and run
# pending traps!  OSH should do this too.

# Related: demo/sigwinch-bug.sh

handler() {
  echo "SIGHUP received"
}

trap handler HUP

echo "PID $$"
#echo "SHELL $SHELL"

# There are several different kinds of 'read', test them all

echo 'read x'
read x
echo
echo "status=$? x=$x"

echo 'read -n 3 y'
read -n 3 y
echo
echo "status=$? y=$y"

echo 'read -d , z'
read -d , z
echo
echo "status=$? z=$z"

echo 'mapfile'
mapfile
echo
echo "status=$? MAPFILE=${MAPFILE[@]}"

#
# OSH only
#

if false; then
  echo 'read --line'
  read --line
  echo
  echo "status=$? _line=$_line"

  echo 'read --all'
  read --all
  echo
  echo "status=$? _all=$_all"
fi
