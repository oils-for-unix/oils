# spec/ysh-stdlib

## our_shell: ysh

#### semaphore
source --builtin synch.ysh

var s = semaNew(1)

{ 
  call semaDown(s)
  echo 1
} &

sleep 0.1

{ 
  call semaDown(s)
  echo 2
} &

echo 3
call semaUp(s)
call semaDestroy(s)
## STDOUT:
1
3
2
## END
