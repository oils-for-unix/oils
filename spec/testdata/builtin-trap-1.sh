
# Why don't other shells run this trap?  It's not a subshell
$SH -c 'trap "echo usr1" USR1; sleep 0.1' &
#$SH -c 'trap "echo int" INT; sleep 0.1' &

sleep 0.05

/usr/bin/kill -USR1 $!

wait

echo status=$?
