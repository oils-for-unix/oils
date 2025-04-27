## oils_failures_allowed: 3
## compare_shells: dash bash mksh

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
## N-I dash status: 2
## N-I mksh status: 1

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

#### wait for N parallel jobs

for i in 3 2 1; do
  { sleep 0.0$i; exit $i; } &
done
wait

# status is lost
echo status=$?

## STDOUT:
status=0
## END

#### wait for N parallel jobs and check failure

set -o errexit

pids=''
for i in 3 2 1; do
  { sleep 0.0$i; echo $i; exit $i; } &
  pids="$pids $!"
done

for pid in $pids; do
  set +o errexit
  wait $pid
  status=$?
  set -o errexit

  echo status=$status
done

## STDOUT:
1
2
3
status=3
status=2
status=1
## END

#### Builtin in background
echo async &
wait
## stdout: async

#### External command in background
sleep 0.01 &
wait
## stdout-json: ""

#### Start background pipeline, wait $pid
echo hi | { exit 99; } &
echo status=$?
wait $!
echo status=$?
echo --

pids=''
for i in 3 2 1; do
  sleep 0.0$i | echo i=$i | ( exit $i ) &
  pids="$pids $!"
done
#echo "PIDS $pids"

for pid in $pids; do
  wait $pid
  echo status=$?
done

# Not cleaned up
if false; then
  echo 'DEBUG'
  jobs --debug
fi

## STDOUT:
status=0
status=99
--
status=3
status=2
status=1
## END

#### Start background pipeline, wait %job_spec
echo hi | { exit 99; } &
echo status=$?
wait %1
echo status=$?
## STDOUT:
status=0
status=99
## END

#### Wait for job and PIPESTATUS

# foreground
{ echo hi; exit 55; } | false
echo status=$? pipestatus=${PIPESTATUS[@]}

# background
{ echo hi; exit 55; } | false &
echo status=$? pipestatus=${PIPESTATUS[@]}

# wait for pipeline
wait %+
#wait %1
#wait $!
echo status=$? pipestatus=${PIPESTATUS[@]}

## STDOUT:
status=1 pipestatus=55 1
status=0 pipestatus=0
status=1 pipestatus=1
## END
## N-I dash status: 2
## N-I dash STDOUT:
## END

#### Wait for job and PIPESTATUS - cat

# foreground
exit 55 | ( cat; exit 99 )
echo status=$? pipestatus=${PIPESTATUS[@]}

# background
exit 55 | ( cat; exit 99 ) &
echo status=$? pipestatus=${PIPESTATUS[@]}

# wait for pipeline
wait %+
#wait %1
#wait $!
echo status=$? pipestatus=${PIPESTATUS[@]}

## STDOUT:
status=99 pipestatus=55 99
status=0 pipestatus=0
status=99 pipestatus=99
## END
## N-I dash status: 2
## N-I dash STDOUT:
## END

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
wait $pid2
echo "status=$?"
wait $pid1
echo "status=$?"
## STDOUT:
status=7
status=9
## END

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
case $SH in (dash|mksh) return ;; esac

{ sleep 0.09; exit 9; } &
{ sleep 0.03; exit 3; } &
wait -n
echo "status=$?"
wait -n
echo "status=$?"
## STDOUT: 
status=3
status=9
## END
## N-I dash/mksh stdout-json: ""

#### Async for loop
for i in 1 2 3; do
  echo $i
  sleep 0.0$i
done &
wait
## STDOUT:
1
2
3
## END
## status: 0

#### Background process doesn't affect parent
echo ${foo=1}
echo $foo
echo ${bar=2} &
wait
echo $bar  # bar is NOT SET in the parent process
## STDOUT:
1
1
2

## END

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

#### jobs prints one line per job
sleep 0.1 & 
sleep 0.1 | cat & 

# dash doesn't print if it's not a terminal?
jobs | wc -l

## STDOUT:
2
## END
## BUG dash STDOUT:
0
## END

#### jobs -p prints one line per job
sleep 0.1 &
sleep 0.1 | cat &

jobs -p > tmp.txt

cat tmp.txt | wc -l  # 2 lines, one for each job
cat tmp.txt | wc -w  # each line is a single "word"

## STDOUT:
2
2
## END


#### No stderr spew when shell is not interactive

# in interactive shell, this prints 'Process' or 'Pipeline'
sleep 0.01 &
sleep 0.01 | cat &
wait

## STDOUT:
## END
## STDERR:
## END


