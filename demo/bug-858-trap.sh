action() {
  echo "from signal"
}

trap 'action' USR1
echo "Run: kill -USR1 $$; date"

# bash/zsh/mksh: wait is interrupted by USR1
# dash: wait is NOT interrupted!

async_test() {
  while true; do
    date
    sleep 5 &
    wait $!
    echo 'next'
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
