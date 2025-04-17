## compare_shells: dash bash mksh zsh ash
## oils_failures_allowed: 5
## oils_cpp_failures_allowed: 4

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

#### Compare \x00 byte versus \x01 byte - command sub

# https://stackoverflow.com/questions/32722007/is-skipping-ignoring-nul-bytes-on-process-substitution-standardized
# bash contains a warning!

# doesn't make sense?

s=$(printf '.\001.')
echo len=${#s}
echo -n "$s" | od -A n -t x1

s=$(printf '.\000.')
echo len=${#s}
echo -n "$s" | od -A n -t x1

s=$(printf '\000')
echo len=${#s} 
echo -n "$s" | od -A n -t x1

## STDOUT:
len=3
 2e 01 2e
len=2
 2e 2e
len=0
## END

## BUG zsh STDOUT:
len=3
 2e 01 2e
len=3
 2e 00 2e
len=1
 00
## END

#### Compare \x00 byte versus \x01 byte - read builtin

# Hm same odd behavior

printf '.\001.' | { read s; echo len=${#s}; echo -n "$s" | od -A n -t x1; }

printf '.\000.' | { read s; echo len=${#s}; echo -n "$s" | od -A n -t x1; }

printf '\000' | { read s; echo len=${#s}; echo -n "$s" | od -A n -t x1; }

## STDOUT:
len=3
 2e 01 2e
len=2
 2e 2e
len=0
## END

## BUG zsh STDOUT:
len=3
 2e 01 2e
len=3
 2e 00 2e
len=1
 00
## END

#### Issue 2269 Reduction

s=$(printf "\000x")
echo len=${#s}  # why is the length of this 1?
echo -n "$s" | od -A n -t x1

# strip one char from the front
s=${s#?}
echo len=${#s}
echo -n "$s" | od -A n -t x1

## STDOUT:
len=1
 78
len=0
## END

## BUG zsh STDOUT:
len=2
 00 78
len=1
 78
## END

#### Issue 2269 - Do NUL bytes match ? in ${a#?}

# https://github.com/oils-for-unix/oils/issues/2269

escape_arg() {
	a="$1"
	until [ -z "$a" ]; do
		case "$a" in
		(\'*) printf "'\"'\"'";;
		(*) printf %.1s "$a";;
		esac
		a="${a#?}"
    echo len=${#a} >&2
	done
}

# encode
phrase="$(escape_arg "that's it!")"
echo phrase "$phrase"

# decode
eval "printf '%s\\n' '$phrase'"

# harder input: NUL surrounded with ::
arg="$(printf ":\000:")" 
#echo "arg=$arg"

exit
arg="$(escape_arg "$arg")"

## STDOUT:
phrase that'"'"'s it!
that's it!
## END
