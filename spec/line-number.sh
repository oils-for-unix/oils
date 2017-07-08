#!/usr/bin/env bash
#
# Demo of line numbers, inspired by:
#
# http://lists.gnu.org/archive/html/bug-bash/2016-12/msg00119.html

# This doesn't appear necessary:
#shopt -s extdebug

main() {
  echo "line number in function: $LINENO"
  trap 'echo line number in trap handler: $LINENO' ERR
  # Start a subshell and exit, which invokes the trap handler.  It uses the function line number?
  # Subshell doesn't have line number attached.
  (exit 17)

  # This uses the command line number.
  #$(exit 17)
}

main
echo "line number at top level: $LINENO"

