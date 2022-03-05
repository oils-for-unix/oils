
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

#### assign readonly -- multiple lines -- set -o posix
set -o posix
readonly x=1
x=2
echo hi
## status: 1
## OK dash/mksh/ash status: 2
## STDOUT:
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

#### First word like foo$x() and foo$[1+2] (regression)

# Problem: $x() func call broke this error message
foo$identity('z')

foo$[1+2]

echo DONE

## status: 2
## OK mksh/zsh status: 1
## STDOUT:
## END
## OK osh status: 0
## OK osh STDOUT:
DONE
## END

#### Function names
foo$x() {
  echo hi
}

foo $x() {
  echo hi
}

## status: 2
## OK mksh/zsh/osh status: 1
## BUG zsh status: 0
## STDOUT:
## END


#### file with NUL byte
echo -e 'echo one \0 echo two' > tmp.sh
$SH tmp.sh
## STDOUT:
one echo two
## END
## N-I dash stdout-json: ""
## N-I dash status: 127
## OK bash stdout-json: ""
## OK bash status: 126
## OK zsh stdout-json: "one \u0000echo two\n"

#### fastlex: PS1 format string that's incomplete / with NUL byte

x=$'\\D{%H:%M'  # leave off trailing }
echo x=${x@P}

## STDOUT:
## END
