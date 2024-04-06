# spec/ysh-stdlib

## our_shell: ysh

#### fifo pipe double closes
source --builtin draft-synch.ysh

fifo-fd-new (&fd)
try {
  fifo-fd-destroy (fd)
}
echo $_status
try {
  fifo-fd-destroy (fd)
}
echo $_status
## STDOUT:
0
1
## END

#### semaphore syncrhonizing async jobs
source --builtin draft-synch.ysh

sema-new (1, &s)
fork { 
  sleep 0.2
  sema-down (s)
  echo 1
}
fork { 
  sleep 0.4
  sema-down (s)
  echo 2
}
fork { 
  sleep 0.6
  sema-down (s)
  echo 3
}
sleep 0.8
echo 4
sema-up (s)
sleep 0.2
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

#### semaphore init with 3, async up once and multiple down
source --builtin draft-synch.ysh

sema-new (3, &s)
fork {
  sleep 0.2
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
