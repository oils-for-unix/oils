#!/bin/bash
#
# Run with different shells to see if you an cancel it.
#
# Usage:
#   $SH ./ctrl-c.sh <function name>

# Cancel this loop
process-loop() {
  while true; do
    echo ---
    sleep 0.01
  done
}

tight-loop() {
  for i in $(seq 1000000); do
    true  # builtin
  done 
}

"$@"
