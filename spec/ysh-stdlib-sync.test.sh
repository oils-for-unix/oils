# spec/ysh-stdlib-sync

## our_shell: ysh

#### fifo pipe double closes
source --builtin draft-sync.ysh

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
source --builtin draft-sync.ysh

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
source --builtin draft-sync.ysh

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
source --builtin draft-sync.ysh

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

#### channel but backed by blocked pipe
source --builtin draft-sync.ysh

channel-new (&ch, __pipe_methods_blocked_netstring(4))

var sent = "I-am-a-pretty-damn-long-string-that-need-to-be-blocked"

fork {
  write -n -- "$sent" | channel-in (ch)
}

var received = $(channel-out (ch))
echo $[received === sent]
## STDOUT:
true
## END

#### RWLock multiple shared lock and free, one exclusive lock
source --builtin draft-sync.ysh

atom-new (&lk)

fork {
  atom-lock-shared (lk)
  echo 1
  sleep 0.3
  atom-unlock (lk)
}
for _ in (0..3) {
  fork {
    sleep 0.1
    atom-lock-shared (lk)
    echo 2
    sleep 0.2
    atom-unlock (lk)
  }
}
sleep 0.1
atom-lock-exclusive (lk)
echo 3
atom-unlock (lk)
atom-destroy (lk)
## STDOUT:
1
2
2
2
3
## END

#### Reading and writing atom
source --builtin draft-sync.ysh

atom-new (&l)
fork {
  atom-lock-exclusive (l)
  write -n 'w' | atom-write-in (l)
  atom-unlock (l)
}
sleep 0.1

for _ in (0..3) {
  fork {
    atom-lock-shared (l)
    atom-read-out (l)
    sleep 0.2
    atom-read-out (l)
    atom-unlock (l)
  }
}
sleep 0.1
write -n y
wait
atom-destroy (l)
write
## STDOUT:
wwwywww
## END

#### Produce many value and exhaust the channel, and then reuse it
source --builtin draft-sync.ysh

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
  setvar sum += i
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
