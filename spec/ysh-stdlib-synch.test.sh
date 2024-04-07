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
      echo $j | channel-in (ch)
    }
  }
}

var sum = 0
for i in (0..16) {
  var cur = $(channel-out (ch)) => int()
  setvar sum += cur
}

echo $sum
channel-destroy (ch)
## STDOUT:
24
## END

#### RWLock multiple shared lock and free, one exclusive lock
source --builtin draft-synch.ysh

rw-lock-new (&lk)

fork {
  rw-lock-shared (lk)
  echo 1
  sleep 0.3
  rw-unlock (lk)
}
for _ in (0..3) {
  fork {
    sleep 0.1
    rw-lock-shared (lk)
    echo 2
    sleep 0.2
    rw-unlock (lk)
  }
}
sleep 0.1
rw-lock-exclusive (lk)
echo 3
rw-unlock (lk)
rw-lock-destroy (lk)
## STDOUT:
1
2
2
2
3
## END

#### Produce many value and exhaust the exhaust the channel once for all, and reuse it
source --builtin draft-synch.ysh

exh-channel-new (&ch)

for i in (0..4) {
  fork { 
    for j in (0..4) { 
      echo $j | exh-channel-in (ch)
    }
  }
}

sleep 0.5
exh-channel-exhaust (ch, &out)
var sum = 0
for i in (out) {
  setvar sum += cur
}
echo $sum
# Reuses the channel
fork {
      echo "yes!" | exh-channel-in (ch)
}
exh-channel-out (ch)
echo
exh-channel-destroy (ch)
## STDOUT:
24
yes!
## END
