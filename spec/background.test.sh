#!/bin/bash
#
# Job control constructs:
#   & terminator (instead of ;)
#   $! -- last PID
#   wait builtin (wait -n waits for next)
#
# Only interactive:
#   fg
#   bg
#   %1 -- current job

### Builtin in background
echo async &
wait
# stdout: async

### External command in background
sleep 0.01 &
wait
# stdout-json: ""

### Pipeline in Background
echo hi | exit 99 &
wait $!
echo status=$?
# stdout: status=99

### Brace group in background, wait all
{ sleep 0.09; exit 9; } &
{ sleep 0.07; exit 7; } &
wait  # wait for all gives 0
echo "status=$?"
# stdout: status=0

### Wait on background process PID
{ sleep 0.09; exit 9; } &
pid1=$!
{ sleep 0.07; exit 7; } &
pid2=$!
wait $pid1
echo "status=$?"
wait $pid2
echo "status=$?"
# stdout-json: "status=9\nstatus=7\n"

### wait -n
{ sleep 0.09; exit 9; } &
{ sleep 0.07; exit 7; } &
wait -n
echo "status=$?"
wait -n
echo "status=$?"
# stdout-json: "status=7\nstatus=9\n"
# N-I dash stdout-json: "status=2\nstatus=2\n"
# N-I mksh stdout-json: "status=1\nstatus=1\n"

### Async for loop
for i in 1 2 3; do
  echo $i
  sleep 0.0$i
done &
wait
# stdout-json: "1\n2\n3\n"
# status: 0

### Background process doesn't affect parent
echo ${foo=1}
echo $foo
echo ${bar=2} &
wait
echo $bar  # bar is NOT SET in the parent process
# stdout-json: "1\n1\n2\n\n"
