#!/usr/bin/env bash
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

#### wait with nothing to wait for
wait
## status: 0

#### wait -n with nothing to wait for
# The 127 is STILL overloaded.  Copying bash for now.
wait -n
## status: 127
## OK dash status: 2
## OK mksh status: 1

#### wait with jobspec syntax %nonexistent
wait %nonexistent
## status: 127
## OK dash status: 2

#### wait with invalid PID
wait 12345678
## status: 127

#### wait with invalid arg
wait zzz
## status: 2
## OK bash status: 1
# mksh confuses a syntax error with 'command not found'!
## BUG mksh status: 127

#### Builtin in background
echo async &
wait
## stdout: async

#### External command in background
sleep 0.01 &
wait
## stdout-json: ""

#### Pipeline in Background
echo hi | { exit 99; } &
wait $!
echo status=$?
## stdout: status=99

#### Wait for job doesn't support PIPESTATUS

# foreground works
{ echo hi; exit 55; } | { exit 99; }
echo pipestatus=${PIPESTATUS[@]}

# background doesn't work
{ echo hi; exit 55; } | { exit 99; } &
wait %+
echo pipestatus=${PIPESTATUS[@]}
## STDOUT:
pipestatus=55 99
pipestatus=99
##
## N-I dash status: 2
## N-I dash stdout-json: ""

#### Brace group in background, wait all
{ sleep 0.09; exit 9; } &
{ sleep 0.07; exit 7; } &
wait  # wait for all gives 0
echo "status=$?"
## stdout: status=0

#### Wait on background process PID
{ sleep 0.09; exit 9; } &
pid1=$!
{ sleep 0.07; exit 7; } &
pid2=$!
wait $pid1
echo "status=$?"
wait $pid2
echo "status=$?"
## stdout-json: "status=9\nstatus=7\n"

#### Wait on multiple specific IDs returns last status
{ sleep 0.08; exit 8; } &
jid1=$!
{ sleep 0.09; exit 9; } &
jid2=$!
{ sleep 0.07; exit 7; } &
jid3=$!
wait $jid1 $jid2 $jid3  # NOTE: not using %1 %2 %3 syntax on purpose
echo "status=$?"  # third job I think
## stdout: status=7

#### wait -n
{ sleep 0.09; exit 9; } &
{ sleep 0.03; exit 3; } &
wait -n
echo "status=$?"
wait -n
echo "status=$?"
## stdout-json: "status=3\nstatus=9\n"
## N-I dash stdout-json: "status=2\nstatus=2\n"
## N-I mksh stdout-json: "status=1\nstatus=1\n"

#### Async for loop
for i in 1 2 3; do
  echo $i
  sleep 0.0$i
done &
wait
## stdout-json: "1\n2\n3\n"
## status: 0

#### Background process doesn't affect parent
echo ${foo=1}
echo $foo
echo ${bar=2} &
wait
echo $bar  # bar is NOT SET in the parent process
## stdout-json: "1\n1\n2\n\n"

#### Background process and then a singleton pipeline

# This was inspired by #416, although that symptom there was timing, so it's
# technically not a regression test.  It's hard to test timing.

{ sleep 0.1; exit 42; } &
echo begin
! true
echo end
wait $!
echo status=$?
## STDOUT:
begin
end
status=42
## END
