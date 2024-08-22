
# ISSUE WITH TEST: & means that trap handler isn't run!
# I guess because the background job gets disconnected from the terminal?
# So it doesn't need SIGINT

# We need some other way to kill it with SIGINT

kill=$(command -v kill)

$SH -c 'trap "echo int" INT; sleep 0.2' &

sleep 0.1

$kill -INT $!

wait

echo status=$?
