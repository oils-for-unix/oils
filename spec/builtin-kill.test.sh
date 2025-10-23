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

#### kill -9 kills the process with SIGKILL
sleep 0.1 & 
pid=$!
kill -9 $pid 
echo kill=$?

wait $pid
echo wait=$?  # 137 is 128 + SIGKILL
## STDOUT:
kill=0
wait=137
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
case $SH in mksh|dash|zsh) exit ;; esac

sleep 0.1 &
pid=$!
builtin kill -s TERM $pid
wait $pid
echo $?
## STDOUT:
143
## N-I dash/mksh/zsh STDOUT:
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

#### Kill with invalid signal
case $SH in dash)  exit ;; esac
sleep 0.1 &
pid=$!
builtin kill -9999 $pid > /dev/null
kill_status=$?
wait $pid
echo $kill_status
## STDOUT:
1
## N-I dash STDOUT:
## END

#### Kills the process with %-
case $SH in mksh|dash) exit ;; esac
sleep 0.5 &
builtin kill -n 9 %-
wait $pid
echo $?
## STDOUT:
0
## N-I dash/mksh STDOUT:
## END

