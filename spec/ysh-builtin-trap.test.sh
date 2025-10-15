## our_shell: ysh

#### trap --remove INT EXIT

trap --add INT EXIT HUP {
  echo one
  echo two
}
trap -p > traps.txt
wc -l traps.txt
echo ---

trap --remove INT EXIT
trap -p > traps.txt
wc -l traps.txt
echo ---

trap --add EXIT { echo 'exit' }

## STDOUT:
3 traps.txt
---
1 traps.txt
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
