# spec/ysh-func

## our_shell: ysh

#### shSplit() respects IFS

var s = ' aa a bb b   '

argv.py @[shSplit(s)]

setvar IFS = 'a'

argv.py @[shSplit(s)]

setvar IFS = 'b'

argv.py @[shSplit(s)]

## STDOUT:
['aa', 'a', 'bb', 'b']
[' ', '', ' ', ' bb b   ']
[' aa a ', '', ' ', '   ']
## END


#### getVar() gets global or local vars

# compare with shvarGet(), which does dynamic scope

proc my-proc {
  var mylocal = 43

  echo g=$[getVar('g')]
  echo mylocal=$[getVar('mylocal')]

  # the whole purpose is dynamic variable names / dynamic binding
  var prefix = 'my'
  echo mylocal=$[getVar(prefix ++ 'local')]

  echo not_global_or_local=$[getVar('not_global_or_local')]
}

proc main {
  var not_global_or_local = 42
  my-proc
}

var g = 'global'

main

## STDOUT:
g=global
mylocal=43
mylocal=43
not_global_or_local=null
## END
