# Demo for https://github.com/oilshell/oil/issues/986
#
# bash and zsh explicitly handle EINTR during the 'read' builtin, and run
# pending traps!  OSH should do this too.

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

echo 'read -d , y'
read -d , y
echo
echo "status=$? z=$z"

echo 'read --all all'
read --all all
echo
echo "status=$? all=$all"

