#
# Tests that explore parsing corner cases.

#### Length of length of ARGS!
fun() { echo ${##}; }
fun 0 1 2 3 4 5 6 7 8 
## stdout: 1

#### Length of length of ARGS!  2 digit
fun() { echo ${##}; }
fun 0 1 2 3 4 5 6 7 8 9
## stdout: 2

#### Is \r considered whitespace?
echo -e 'echo\rTEST' > myscript
$SH myscript

## status: 127
## STDOUT:
## END
