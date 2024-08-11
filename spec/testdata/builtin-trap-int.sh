
# ISSUE WITH TEST: & means that trap handler isn't run!
# I guess because the background job gets disconnected from the terminal?
# So it doesn't need SIGINT

# We need some other way to kill it with SIGINT

$SH -c 'trap "echo int" INT; sleep 0.1' &

sleep 0.05

$(command -v kill) -INT $!

wait

echo status=$?
