
#### echo keyword
echo done
## stdout: done

#### if/else
if false; then
  echo THEN
else
  echo ELSE
fi
## stdout: ELSE

#### Turn an array into an integer.
a=(1 2 3)
(( a = 42 )) 
echo $a
## stdout: 42
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2


#### assign readonly -- one line
readonly x=1; x=2; echo hi
## status: 1
## OK dash/mksh/ash status: 2
## STDOUT:
## END

#### assign readonly -- multiple lines
readonly x=1
x=2
echo hi
## status: 1
## OK dash/mksh/ash status: 2
## STDOUT:
## END
## BUG bash status: 0
## BUG bash STDOUT:
hi
## END

#### unset readonly -- one line
readonly x=1; unset x; echo hi
## STDOUT:
hi
## END
## OK dash/ash status: 2
## OK zsh status: 1
## OK dash/ash stdout-json: ""
## OK zsh stdout-json: ""

#### unset readonly -- multiple lines
readonly x=1
unset x
echo hi
## OK dash/ash status: 2
## OK zsh status: 1
## OK dash/ash stdout-json: ""
## OK zsh stdout-json: ""
