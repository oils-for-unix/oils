## our_shell: ysh
## oils_failures_allowed: 0

#### captureStdout() is like $()

proc p {
  var captured = 'captured'
  var cmd = ^(echo one; echo $captured)
  
  var stdout = io.captureStdout(cmd)
  pp test_ (stdout)
}

p

## STDOUT:
(Str)   "one\ncaptured"
## END

#### captureStdout() failure

var c = ^(echo one; false; echo two)

# Hm this prints a message, but no stack trace
# Should make it fail I think

try {
  var x = io.captureStdout(c)
}
# This has {"code": 3} because it's an expression error.  Should probably
pp test_ (_error)

var x = io.captureStdout(c)

## status: 4
## STDOUT:
(Dict)   {"status":1,"code":4,"message":"captureStdout(): command failed with status 1"}
## END

#### io->eval() is like eval builtin

var c = ^(echo one; echo two)
var status = io->eval(c)

# doesn't return anything
echo status=$status

## STDOUT:
one
two
status=null
## END

#### io->eval() with failing command - caller must handle

var c = ^(echo one; false; echo two)

try {
  call io->eval(c)
}
pp test_ (_error)

call io->eval(c)

## status: 1
## STDOUT:
one
(Dict)   {"code":1}
one
## END

#### io->eval() with exit

var c = ^(echo one; exit; echo two)

try {
  call io->eval(c)
}
echo 'we do not get here'
pp test_ (_error)


## STDOUT:
one
## END

