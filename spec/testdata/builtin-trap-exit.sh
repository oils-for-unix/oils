kill=$(command -v kill)

# Why don't other shells run this trap?  It's not a subshell
$SH -c 'trap "echo on exit" EXIT; sleep 0.1' &

sleep 0.05

# Note: this is SIGINT, for the KeyboardInterrupt problem
$kill -INT $!

wait

echo status=$?
