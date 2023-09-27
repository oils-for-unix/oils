# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 0

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

#### Eval a command sub
eval (^(echo block literal))
## STDOUT:
block literal
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
