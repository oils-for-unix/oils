
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
## OK osh STDOUT:
one
## END
## N-I dash stdout-json: ""
## N-I dash status: 127
## OK bash stdout-json: ""
## OK bash status: 126
## OK zsh stdout-json: "one \u0000echo two\n"

#### fastlex: PS1 format string that's incomplete / with NUL byte
case $SH in bash) exit ;; esac

x=$'\\D{%H:%M'  # leave off trailing }
echo x=${x@P}

## STDOUT:
x=\D{%H:%M
## END

# bash just ignores the missing }
## BUG bash stdout-json: ""

# These shells don't understand @P

## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2

## N-I zsh stdout-json: ""
## N-I zsh status: 1


#### 'echo' and printf to disk full

# Inspired by https://blog.sunfishcode.online/bugs-in-hello-world/

echo hi > /dev/full
echo status=$?
printf '%s\n' hi > /dev/full
echo status=$?

## STDOUT:
status=1
status=1
## END

#### subshell while running a script (regression)
# Ensures that spawning a subshell doesn't cause a seek on the file input stream
# representing the current script (issue #1233).
cat >tmp.sh <<'EOF'
echo start
(:)
echo end
EOF
$SH tmp.sh
## STDOUT:
start
end
## END

#### for loop (issue #1446)
case $SH in (dash|mksh|ash) exit ;; esac

for (( n=0; n<(3-(1)); n++ )) ; do echo $n; done

## STDOUT:
0
1
## END
## N-I dash/mksh/ash STDOUT:
## END



#### for loop 2 (issue #1446)
case $SH in (dash|mksh|ash) exit ;; esac


for (( n=0; n<(3- (1)); n++ )) ; do echo $n; done

## STDOUT:
0
1
## END
## N-I dash/mksh/ash STDOUT:
## END

#### autoconf word split (#1449)

mysed() {
  for line in "$@"; do
    echo "[$line]"
  done
}

sedinputs="f1 f2"
sedscript='my sed command'

# Parsed and evaluated correctly: with word_part.EscapedLiteral \"

x=$(eval "mysed -n \"\$sedscript\" $sedinputs")
echo '--- $()'
echo "$x"

# With backticks, the \" gets lost somehow

x=`eval "mysed -n \"\$sedscript\" $sedinputs"`
echo '--- backticks'
echo "$x"


# Test it in a case statement

case `eval "mysed -n \"\$sedscript\" $sedinputs"` in 
  (*'[my sed command]'*)
    echo 'NOT SPLIT'
    ;;
esac

## STDOUT:
--- $()
[-n]
[my sed command]
[f1]
[f2]
--- backticks
[-n]
[my sed command]
[f1]
[f2]
NOT SPLIT
## END

#### autoconf arithmetic - relaxed eval_unsafe_arith (#1450)

as_fn_arith ()
{
    as_val=$(( $* ))
}
as_fn_arith 1 + 1
echo $as_val

## STDOUT:
2
## END

#### command execution $(echo 42 | tee PWNED) not allowed

rm -f PWNED

x='a[$(echo 42 | tee PWNED)]=1'
echo $(( x ))

if test -f PWNED; then
  cat PWNED
else
  echo NOPE
fi

## status: 1
## OK dash/ash status: 2
## stdout-json: ""
## BUG bash/mksh/zsh status: 0
## BUG bash/mksh/zsh STDOUT:
1
42
## END

#### process sub <(echo 42 | tee PWNED) not allowed

rm -f PWNED

x='a[<(echo 42 | tee PWNED)]=1'
echo $(( x ))

if test -f PWNED; then
  cat PWNED
else
  echo NOPE
fi

## status: 1
## stdout-json: ""

## OK dash/ash status: 2

# bash keeps going
## BUG bash status: 0
## BUG bash STDOUT:
NOPE
## END


#### unset doesn't allow command execution

typeset -a a  # for mksh
a=(42)
echo len=${#a[@]}

unset -v 'a[$(echo 0 | tee PWNED)]'
echo len=${#a[@]}

if test -f PWNED; then
  echo PWNED
  cat PWNED
else
  echo NOPE
fi

## status: 1
## STDOUT:
len=1
## END

## N-I dash/ash status: 2
## N-I dash/ash stdout-json: ""

## BUG bash/mksh status: 0
## BUG bash/mksh STDOUT:
len=1
len=0
PWNED
0
## END

## BUG zsh status: 0
## BUG zsh STDOUT:
len=1
len=1
PWNED
0
## END

