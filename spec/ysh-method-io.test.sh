## our_shell: ysh
## oils_failures_allowed: 0

#### captureStdout() is like $()

var c = ^(echo one; echo two)

var y = io.captureStdout(c)
pp test_ (y)

## STDOUT:
(Str)   "one\ntwo"
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

#### _io->eval() is like eval builtin

var c = ^(echo one; echo two)
var status = _io->eval(c)

# doesn't return anything
echo status=$status

## STDOUT:
one
two
status=null
## END

#### _io->eval() with failing command - caller must handle

var c = ^(echo one; false; echo two)

try {
  call _io->eval(c)
}
pp test_ (_error)

call _io->eval(c)

## status: 1
## STDOUT:
one
(Dict)   {"code":1}
one
## END

#### _io->eval() with exit

var c = ^(echo one; exit; echo two)

try {
  call _io->eval(c)
}
echo 'we do not get here'
pp test_ (_error)


## STDOUT:
one
## END

