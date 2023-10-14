# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 2

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
proc lazy-block (out Ref;;; block) {
  setref out = block
}

var myglobal = 0

lazy-block :my_block {
  json write (myglobal)
}

eval (my_block)
setvar myglobal = 1
eval (my_block)
## STDOUT:
0
1
## END

#### Eval should not have dynamic scope
proc leaky (;;; block) {
  var this = 42
  eval (block)
}

leaky {
  echo $this
}
## status: 1
## STDOUT:
## END
