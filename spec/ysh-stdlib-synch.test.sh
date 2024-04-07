# spec/ysh-stdlib

## our_shell: ysh

#### fifo pipe double closes
source --builtin draft-synch.ysh

fifo-fd-new (&fd)
try {
  fifo-fd-destroy (fd)
}
echo $_status
fifo-fd-destroy (fd)
## status: 1
## STDOUT:
0
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

#### channel reads and writes
source --builtin draft-synch.ysh

channel-new (&ch)

for i in (0..4) {
  fork { 
    for j in (0..4) { 
      echo $j | channel-pipe-in (ch)
    }
  }
}

var sum = 0
for i in (0..16) {
  var cur = $(channel-pipe-out (ch)) => int()
  setvar sum += cur
}

echo $sum
## STDOUT:
24
## END
