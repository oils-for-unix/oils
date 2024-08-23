
kill=$(command -v kill)

$SH -c 'trap "echo usr1" USR1; sleep 0.2' &

sleep 0.1

$kill -USR1 $!

wait

echo status=$?
