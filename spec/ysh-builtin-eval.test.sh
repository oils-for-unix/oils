# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 1

#### Eval does not take a literal block - can restore this later

var b = ^(echo obj)
eval (b)

eval (^(echo command literal))

# Doesn't work because it's a positional arg
eval { echo block }

## status: 3
## STDOUT:
obj
command literal
## END


#### Eval a block within a proc
proc run (;;; block) {
  eval (block)
}

run {
  echo 'In a block!'
}
## STDOUT:
In a block!
## END

#### Eval block created by calling a proc
proc lazy-block ( ; out; ; block) {
  call out->setValue(block)
}

var myglobal = 0

lazy-block (&my_block) {
  json write (myglobal)
}

eval (my_block)
setvar myglobal = 1
eval (my_block)
## STDOUT:
0
1
## END

#### eval (block) can read variables like eval ''

proc p2(code_str) {
  var mylocal = 42
  eval $code_str
}

p2 'echo mylocal=$mylocal'

proc p (;;; block) {
  var mylocal = 99
  eval (block)
}

p {
  echo mylocal=$mylocal
}


## STDOUT:
mylocal=42
mylocal=99
## END

#### eval should have a sandboxed mode

proc p (;;; block) {
  var this = 42

  # like push-registers?  Not sure
  # We could use state.ctx_Temp ?  There's also ctx_FuncCall etc.
  #
  # I think we want to provide full control over the stack.
  push-frame {
    eval (block)
  }
}

p {
  echo $this
}

## status: 1
## STDOUT:
TODO
## END


#### eval 'mystring' vs. eval (myblock)

eval 'echo plain'
echo plain=$?
var b = ^(echo plain)
eval (b)
echo plain=$?

echo

# This calls main_loop.Batch(), which catches
# - error.Parse
# - error.ErrExit
# - error.FatalRuntime - glob errors, etc.?

try {
  eval 'echo one; false; echo two'
}
pp line (_error)

# This calls CommandEvaluator.EvalCommand(), as blocks do

var b = ^(echo one; false; echo two)
try {
  eval (b)
}
pp line (_error)

## STDOUT:
plain
plain=0
plain
plain=0

one
(Dict)   {"code":1}
one
(Dict)   {"code":1}
## END
