# spec/ysh-stdlib

## our_shell: ysh

#### semaphore
source --builtin draft-synch.ysh

sema-new (1, &s)
fork { 
  sleep 0.5
  sema-down (s)
  echo 1
}
fork { 
  sleep 1
  sema-down (s)
  echo 2
}
fork { 
  sleep 1.5
  sema-down (s)
  echo 3
}
sleep 2
echo 4
sema-up (s)
sleep 0.5
echo 5
sema-up (s)
sema-destroy (s)
## STDOUT:
1
4
2
5
3
## END

#### semaphore init and multiple down
source --builtin draft-synch.ysh

sema-new (3, &s)
fork {
  sleep 1
  sema-up (s) 
}
sema-down (s)
sema-down (s)
sema-down (s)
sema-down (s)
echo yes
## STDOUT:
yes
## END

# TODO: add test case for mutex and other sync primitives
