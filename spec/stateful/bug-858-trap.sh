# If this is on, wait will exit
#set -o errexit

action() {
  echo "from signal"
}

# wait has an exit code according to the signal!
trap 'action' USR1
trap 'action' USR2

echo "Run: kill -USR1 $$; date"

# bash/zsh/mksh: wait is interrupted by USR1
# dash: wait is NOT interrupted!

async_test() {
  while true; do
    date
    sleep 5 &
    wait $!
    echo wait=$?
  done
}

async_test2() {
  echo 'with wait -n'
  while true; do
    date
    sleep 5 &
    wait -n
    echo wait=$?
  done
}

async_test3() {
  echo 'with wait'
  while true; do
    date
    sleep 5 &
    wait
    echo wait=$?
  done
}

# bash/dash/zsh/mksh: signal handler run after sleep
sync_test() {
  while true; do
    date
    sleep 5
    echo 'next'
  done
}

"$@"
