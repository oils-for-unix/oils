
# Why don't other shells run this trap?  It's not a subshell
$SH -c 'trap "echo int" INT; sleep 0.1' &

sleep 0.05

$(command -v kill) -INT $!

wait

echo status=$?
