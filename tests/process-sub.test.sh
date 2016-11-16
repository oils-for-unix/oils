#!/bin/bash

### Process sub input
f=_tmp/process-sub.txt
{ echo 1; echo 2; echo 3; } > $f
comm <(head -n 2 $f) <(tail -n 2 $f)
# stdout-json: "1\n\t\t2\n\t3\n"
