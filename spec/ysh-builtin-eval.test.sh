# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 1

#### Eval a command literal

var b = ^(echo obj)
eval (b)

eval (^(echo command literal))

eval { echo block }

## STDOUT:
obj
command literal
block
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
  :: out->setValue(block)
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
