## our_shell: ysh
## oils_failures_allowed: 1

# TODO: have to fix the pipe issue

#### trap --remove INT EXIT

trap --add INT EXIT HUP {
  echo one
  echo two
}
trap -p
echo ---

trap --remove INT EXIT
trap -p
echo ---

trap --add EXIT { echo 'exit' }

## STDOUT:
trap -- 'echo hi' EXIT
trap -- 'echo hi' SIGHUP
trap -- 'echo hi' SIGINT
---
trap -- 'echo hi' SIGHUP
---
exit
## END

#### trap block arg is a not a closure - like cd and other builtins

# e.g. We're not using ctx_EnclosedFrame in RunTrapsOnExit() and in the signal
# handlers.  It's more similar to OSH.

var x = 'global'

proc register {
  var x = 'local'
  trap --add EXIT {
     echo "x = $x"
  }
}

register

## STDOUT:
x = global
## END
