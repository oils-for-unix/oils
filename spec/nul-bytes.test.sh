## compare_shells: dash bash mksh zsh ash
## oils_failures_allowed: 2
## oils_cpp_failures_allowed: 1

#### NUL bytes with echo -e
case $SH in (dash) exit ;; esac

echo -e '\0-'
#echo -e '\x00-'
#echo -e '\000-'

## stdout-repr: "\x00-\n"
## BUG zsh stdout-repr: "\x00\n"
## N-I dash stdout-json: ""

#### NUL bytes in printf format
printf '\0\n'
## stdout-repr: "\x00\n"

#### NUL bytes in printf value (OSH and zsh agree)
case $SH in (dash) exit ;; esac

nul=$'\0'
echo "$nul"
printf '%s\n' "$nul"

## stdout-repr: "\n\n"
## OK osh/zsh stdout-repr: "\x00\n\x00\n"
## N-I dash stdout-json: ""



#### NUL bytes with echo $'\0' (OSH and zsh agree)

case $SH in (dash) exit ;; esac

# OSH agrees with ZSH -- so you have the ability to print NUL bytes without
# legacy echo -e

echo $'\0'

## stdout-repr: "\n"
## OK osh/zsh stdout-repr: "\0\n"
## N-I dash stdout-json: ""


#### NUL bytes and IFS splitting
case $SH in (dash) exit ;; esac

argv.py $(echo -e '\0')
argv.py "$(echo -e '\0')"
argv.py $(echo -e 'a\0b')
argv.py "$(echo -e 'a\0b')"

## STDOUT:
[]
['']
['ab']
['ab']
## END
## BUG zsh STDOUT:
['', '']
['']
['a', 'b']
['a']
## END

## N-I dash STDOUT:
## END

#### NUL bytes with test -n

case $SH in (dash) exit ;; esac

# zsh is buggy here, weird
test -n $''
echo status=$?

test -n $'\0'
echo status=$?


## STDOUT:
status=1
status=1
## END
## OK osh STDOUT:
status=1
status=0
## END
## BUG zsh STDOUT:
status=0
status=0
## END

## N-I dash STDOUT:
## END


#### NUL bytes with test -f

case $SH in (dash) exit ;; esac


test -f $'\0'
echo status=$?

touch foo
test -f $'foo\0'
echo status=$?

test -f $'foo\0bar'
echo status=$?

test -f $'foobar'
echo status=$?


## STDOUT:
status=1
status=0
status=0
status=1
## END

## OK ash STDOUT:
status=1
status=0
status=1
status=1
## END

## N-I dash STDOUT:
## END


#### NUL bytes with ${#s} (OSH and zsh agree)

case $SH in (dash) exit ;; esac

empty=$''
nul=$'\0'

echo empty=${#empty}
echo nul=${#nul}


## STDOUT:
empty=0
nul=0
## END

## OK osh/zsh STDOUT:
empty=0
nul=1
## END

## N-I dash STDOUT:
## END
