## oils_failures_allowed: 0
## compare_shells: dash bash mksh zsh

# Tests for builtins having to do with killing a process

#### kill -15 kills the process with SIGTERM
sleep 0.1 &
pid=$!
kill -15 $pid
echo kill=$?

wait $pid
echo wait=$?  # 143 is 128 + SIGTERM
## STDOUT:
kill=0
wait=143
## END
## BUG mksh STDOUT:
kill=0
wait=0
## END

#### kill -KILL kills the process with SIGKILL
sleep 0.1 & 
pid=$!
kill -KILL $pid 
echo kill=$?

wait $pid
echo wait=$?  # 137 is 128 + SIGKILL
## STDOUT:
kill=0
wait=137
## END
## N-I zsh STDOUT:
kill=1
wait=0
## END

#### kill -n 9 specifies the signal number
#case $SH in mksh|dash) exit ;; esac

sleep 0.1 &
pid=$!
kill -n 9 $pid
echo kill=$?

wait $pid
echo wait=$?
## STDOUT:
kill=0
wait=137
## END
## N-I dash STDOUT:
kill=2
wait=0
## END
## N-I mksh STDOUT:
kill=1
wait=0
## END

#### kill -s TERM specifies the signal name
sleep 0.1 &
pid=$!
kill -s TERM $pid
echo kill=$?

wait $pid
echo wait=$?
## STDOUT:
kill=0
wait=143
## END
## BUG mksh STDOUT:
kill=0
wait=0
## END
## N-I zsh STDOUT:
kill=1
wait=0
## END

#### kill SIGTERM, rather than kill -SIGTERM
# Test 3: SIGTERM with sigspec variants
case $SH in mksh|dash|zsh) exit ;; esac

sleep 0.1 &
pid=$!
builtin kill SIGTERM $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

sleep 0.1 &
pid=$!
builtin kill SigTERM $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

sleep 0.1 &
pid=$!
builtin kill sigterm $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

sleep 0.1 &
pid=$!
builtin kill TERM $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

sleep 0.1 &
pid=$!
builtin kill term $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

sleep 0.1 &
pid=$!
builtin kill TErm $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)

## STDOUT:
143
143
143
143
143
143
## N-I dash/mksh/zsh STDOUT:
## END

#### kill -l shows signals
case $SH in dash) exit ;; esac

# Check if at least the HUP flag is reported.  The output format of all shells
# is different and the available signals may depend on your environment

builtin kill -l | grep HUP > /dev/null
echo $?
## STDOUT:
0
## N-I dash STDOUT:
## END

#### kill -L also shows signals
case $SH in mksh|dash|zsh) exit ;; esac

builtin kill -L | grep HUP > /dev/null
echo $?
## STDOUT:
0
## N-I mksh/dash/zsh STDOUT:
## END

#### kill -l 10 TERM translates between names and numbers
case $SH in mksh|dash) exit ;; esac

builtin kill -l 10 11 12
echo

builtin kill -l SIGUSR1 SIGSEGV USR2
echo

# mixed kind
builtin kill -l 10 SIGSEGV 12

## STDOUT:
USR1
SEGV
USR2

10
11
12

USR1
11
USR2
## N-I dash/mksh STDOUT:
## END

#### kill -9999 is an invalid signal
case $SH in dash)  exit ;; esac
sleep 0.1 &
pid=$!
kill -9999 $pid > /dev/null
echo kill=$?

wait $pid
echo wait=$?
## STDOUT:
kill=1
wait=0
## N-I dash STDOUT:
## END

#### kill -15 %% kills current job
#case $SH in mksh|dash) exit ;; esac

sleep 0.5 &

kill -15 %%
echo kill=$?

wait %%
echo wait=$?

# no such job
wait %%
echo wait=$?

## STDOUT:
kill=0
wait=143
wait=127
## END
## OK zsh STDOUT:
kill=0
wait=143
wait=1
## END
## N-I dash STDOUT:
kill=1
wait=0
wait=0
## END
## BUG mksh STDOUT:
kill=0
wait=0
wait=127
## END

#### kill -15 %- kills previous job
#case $SH in mksh|dash) exit ;; esac

sleep 0.1 &  # previous job
sleep 0.2 &  # current job

kill -15 %-
echo kill=$?

wait %-
echo wait=$?

# what does bash define here as the previous job?  May be a bug
#wait %-
#echo wait=$?

## STDOUT:
kill=0
wait=143
## END
## BUG mksh STDOUT:
kill=0
wait=0
## END

