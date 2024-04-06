# spec/ysh-stdlib

## our_shell: ysh

#### semaphore
source --builtin synch.ysh

var s = sema-new(1)
{ 
  sleep 0.5
  call sema-down(s)
  echo 1
} &
{ 
  sleep 1
  call sema-down(s)
  echo 2
} &
{ 
  sleep 1.5
  call sema-down(s)
  echo 3
} &
sleep 2
echo 4
call sema-up(s)
sleep 0.5
echo 5
call sema-up(s)
call sema-destroy(s)
## STDOUT:
1
4
2
5
3
## END

#### semaphore init and multiple down
source --builtin synch.ysh

var s = sema-new(3)
{
  sleep 1
  call sema-up(s) 
} &
call sema-down(s)
call sema-down(s)
call sema-down(s)
call sema-down(s)
echo yes
## STDOUT:
yes
## END

# TODO: add test case for mutex and other sync primitives
