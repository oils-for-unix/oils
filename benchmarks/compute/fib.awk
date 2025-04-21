#!/usr/bin/awk -f

# Usage: awk -f fib.awk n=10 iters=3

BEGIN {

iters = ARGV[1] ? ARGV[1] : 5
n =     ARGV[2] ? ARGV[2] : 10

i = 0
while (i < iters) {

    # Initialize first two numbers
    a = 1
    b = 1

    j = 0

    while (j < n) {
        tmp = b
        b = a + b
        a = tmp

        j++
    }
    print b

    i++
}

} # BEGIN
