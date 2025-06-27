## our_shell: ysh
## oils_failures_allowed: 10000

#### Unless syntax sugar
macro unless (; cond ;; block) {
  return (quote {
    if (not (unquote cond)) {
      (unquote block)
    }
  })
}

unless (1 > 2) {
  echo rocks
}
## status: 0
## STDOUT:
rocks
## END

#### withMutex syntax sugar
proc mutexCreate() {
  var mutexPath = $(mktemp)
}
macro withMutex (; ...mutexesWithBlk) {
  if (len(mutexesWithBlk) == 1) {
    return (mutexesWithBlk[0])
  } else {
    var mutexesRest = mutexesWithBlk[1:]
    var mutexCurrent = mutexesWithBlk[0]
    return (
      quote {
        {
          if flock $fd {
            unquote (withMutex (...mutexesRest))
          } else {
            echo "Failed to grab the lock `$mutexCurrent`"
            exit 1
          }
        } {fd}<$mutexCurrent
      }
    )
  }
}

var lock1 = mutexCreate
var lock2 = mutexCreate
var lock3 = mutexCreate
withMutex (lock1, lock2, lock3) {
  echo rocks
}
## status: 0
## STDOUT:
rocks
## END



