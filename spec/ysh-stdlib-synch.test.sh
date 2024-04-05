# spec/ysh-stdlib

## our_shell: ysh

#### semaphore
source --builtin synch.ysh

var s = semaNew(1)
{ 
  call semaDown(s)
  echo 1
} &
{ 
  sleep 1
  call semaDown(s)
  echo 2
} &
{ 
  sleep 2
  call semaDown(s)
  echo 3
} &
echo 4
call semaUp(s)
echo 5
call semaUp(s)
call semaDestroy(s)
## STDOUT:
1
4
2
5
3
## END

#### semaphore init and multiple down
source --builtin synch.ysh

var s = semaNew(4)

call semaDown(s)
call semaDown(s)
call semaDown(s)
call semaDown(s)
echo yes
## STDOUT:
yes
## END

# TODO: add test case for mutex and jobqueue
