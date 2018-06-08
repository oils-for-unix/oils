#!/bin/bash

### trap -l
trap -l | grep INT >/dev/null
## status: 0
## N-I dash/mksh status: 1

### trap -p
trap 'echo exit' EXIT
trap -p | grep EXIT >/dev/null
## status: 0
## N-I dash/mksh status: 1

### Register invalid trap
trap 'foo' SIGINVALID
## status: 1

### Remove invalid trap
trap - SIGINVALID
## status: 1

### SIGINT and INT are aliases
trap - SIGINT
echo $?
trap - INT
echo $?
## STDOUT:
0
0
## END
## N-I dash STDOUT:
1
0
## END

### Invalid trap invocation
trap 'foo'
echo status=$?
## stdout: status=1
## OK bash stdout: status=2
## BUG mksh stdout: status=0

### exit 1 when trap code string is invalid
# All shells spew warnings to stderr, but don't actually exit!  Bad!
trap 'echo <' EXIT
echo status=$?
## stdout: status=1
## BUG mksh status: 1
## BUG mksh stdout: status=0
## BUG dash/bash status: 0
## BUG dash/bash stdout: status=0

### trap EXIT
cleanup() {
  echo "cleanup [$@]"
}
trap 'cleanup x y z' EXIT
## stdout: cleanup [x y z]

### trap DEBUG
debuglog() {
  echo "debuglog [$@]"
}
trap 'debuglog x y' DEBUG
echo 1
echo 2
## STDOUT:
debuglog [x y]
1
debuglog [x y]
2
## END
## N-I dash/mksh STDOUT:
1
2
## END

### trap RETURN
profile() {
  echo "profile [$@]"
}
g() {
  echo --
  echo g
  echo --
  return
}
f() {
  echo --
  echo f
  echo --
  g
}
# RETURN trap doesn't fire when a function returns, only when a script returns?
# That's not what the manual syas.
trap 'profile x y' RETURN
f
. spec/testdata/return-helper.sh
## status: 42
## STDOUT:
--
f
--
--
g
--
return-helper.sh
profile [x y]
## END
## N-I dash/mksh status: 42
## N-I dash/mksh STDOUT:
--
f
--
--
g
--
return-helper.sh
## END

### trap ERR and disable it
err() {
  echo "err [$@] $?"
}
trap 'err x y' ERR 
echo 1
false
echo 2
trap - ERR  # disable trap
false
echo 3
## STDOUT:
1
err [x y] 1
2
3
## END
# N-I dash STDOUT:
1
2
3
## END
