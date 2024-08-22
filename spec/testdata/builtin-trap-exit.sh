
# Why don't other shells run this trap?  It's not a subshell
$SH -c 'trap "echo on exit" EXIT; sleep 0.1' &

sleep 0.02

# Note: this is SIGINT, for the KeyboardInterrupt problem
$(command -v kill) -INT $!

wait

echo status=$?
