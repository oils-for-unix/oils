## oils_failures_allowed: 0
## compare_shells: dash bash mksh zsh

# Tests for builtins having to do with killing a process

#### Kills the process with SIGTERM
# Test 1: Basic SIGTERM
sleep 0.1 &
pid=$!
builtin kill -15 $pid
wait $pid
echo $?  # Should be 143 (128 + SIGTERM)
## STDOUT:
143
## END
# For some reason mksh doesn't return the same as the others.
## OK mksh stdout: 0
## OK dash stdout: 0

#### Kills the process with SIGKILL
# Test 2: Basic SIGKILL
sleep 0.1 & 
pid=$!
builtin kill -9 $pid 
wait $pid
echo $?  # Must be 137 (128 + SIGKILL) 
## STDOUT:
137
## END
## OK dash stdout: 0

#### Kill the process with -sigspec
# Test 3: SIGTERM with sigspec variants
case $SH in mksh|dash|zsh) echo 'skip'; exit ;; esac

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
## END
## N-I dash/mksh/zsh STDOUT:
skip
#### List available signals
# check if at least the HUP flag is reported
# the output format of all shells is different and the
# available flags may depend on your environment
# TODO: check at least if all posix flags are listed?
case $SH in dash) echo 'skip'; exit ;; esac
builtin kill -l | grep HUP > /dev/null
echo $?
## STDOUT:
0
## END
## N-I dash stdout: skip

#### List available signals with -L
# check if at least the HUP flag is reported
# the output format of all shells is different and the
# available flags may depend on your environment
# TODO: check at least if all posix flags are listed?
case $SH in mksh|dash|zsh) echo 'skip'; exit ;; esac
builtin kill -L | grep HUP > /dev/null
echo $?
## STDOUT:
0
## END
## N-I mksh/dash/zsh stdout: skip


#### Kill with invalid signal
case $SH in dash) echo 'skip'; exit ;; esac
sleep 0.1 &
pid=$!
builtin kill -9999 $pid > /dev/null
kill_status=$?
wait $pid
echo $kill_status
## STDOUT:
1
## END
## N-I dash stdout: skip

#### Kills the process with -n 9
case $SH in mksh|dash) echo 'skip'; exit ;; esac
sleep 0.1 &
pid=$!
builtin kill -n 9 $pid
wait $pid
echo $?
## STDOUT:
137
## END
## N-I dash/mksh stdout: skip

