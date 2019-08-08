# Oil builtins

#### push onto a=(1 2)
shopt -s oil-parse-at
a=(1 2)
push a _ '3 4' '5'
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END

#### push onto var a = @(1 2)
shopt -s oil-parse-at
var a = @(1 2)
push a _ '3 4' '5'
argv.py @a
## STDOUT:
['1', '2', '3 4', '5']
## END
