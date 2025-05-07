## oils_failures_allowed: 2
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
