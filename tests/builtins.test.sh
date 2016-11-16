#!/bin/bash

### time block
# bash and mksh work; dash does't.  TODO: test substring
{ time { sleep 0.01; sleep 0.02; } } 2>_tmp/time.txt
cat _tmp/time.txt | grep --only-matching real
# Just check that we found 'real'.
# This is fiddly:
# | sed -n -E -e 's/.*(0m0\.03).*/\1/'
#
# status: 0
# stdout: real
# BUG dash status: 2
# BUG dash stdout-json: ""

### Exit builtin
exit 3
# status: 3

### Exit builtin with invalid arg 
exit invalid
# Rationale: runtime errors are 1
# status: 1
# OK dash/bash status: 2
