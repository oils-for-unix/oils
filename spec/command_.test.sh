#!/bin/bash
#
# Miscellaneous tests for the command language.

### Chained && and || -- there is no precedence
expr 1 && expr 2 || expr 3 && expr 4
echo "status=$?"
# stdout-json: "1\n2\n4\nstatus=0\n"

### Command block
{ which ls; }
# stdout: /bin/ls

