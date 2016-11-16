#!/bin/bash

### (( )) result
(( 1 )) && echo True
(( 0 )) || echo False
# stdout-json: "True\nFalse\n"

### negative number is true
(( -1 )) && echo True
# stdout: True

### (( )) in if statement
if (( 3 > 2)); then
  echo True
fi
# stdout: True
