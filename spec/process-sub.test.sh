#!/usr/bin/env bash

### Process sub input
f=_tmp/process-sub.txt
{ echo 1; echo 2; echo 3; } > $f
comm <(head -n 2 $f) <(tail -n 2 $f)
# stdout-json: "1\n\t\t2\n\t3\n"

### Non-linear pipeline with >()
stdout_stderr() {
  echo o1
  echo o2

  sleep 0.1  # Does not change order

  { echo e1;
    echo warning: e2 
    echo e3;
  } >& 2
}
stdout_stderr 2> >(grep warning) | tac >$TMP/out.txt
wait $!  # this does nothing in bash 4.3, but probably does in bash 4.4.
echo OUT
cat $TMP/out.txt
# PROBLEM -- OUT comes first, and then 'warning: e2', and then 'o2 o1'.  It
# looks like it's because nobody waits for the proc sub.
# http://lists.gnu.org/archive/html/help-bash/2017-06/msg00018.html
# stdout-json: "OUT\nwarning: e2\no2\no1\n"
