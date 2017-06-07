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

### Brace group in background
{ sleep 0.01; exit 99; } & wait; echo $?
# stdout: 0
# status: 0

### Wait on background process PID
{ sleep 0.01; exit 99; } & wait $!; echo $?
# stdout: 99
# status: 0

### Builtin in background
echo async & wait
# stdout: async
# status: 0

### Async for loop
for i in 1 2 3; do
  echo $i
  sleep 0.0$i
done & wait
# stdout-json: "1\n2\n3\n"
# status: 0

### Background process doesn't affect parent
echo ${foo=1}
echo $foo
echo ${bar=2} &
wait
echo $bar  # bar is NOT SET in the parent process
# stdout-json: "1\n1\n2\n\n"
