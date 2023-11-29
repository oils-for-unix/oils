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

