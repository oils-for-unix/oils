## compare_shells: dash bash mksh zsh ash
## oils_failures_allowed: 7
## oils_cpp_failures_allowed: 6

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

show_bytes() {
  echo -n "$1" | od -A n -t x1
}

s=$(printf '.\001.')
echo len=${#s}
show_bytes "$s"

s=$(printf '.\000.')
echo len=${#s}
show_bytes "$s"

s=$(printf '\000')
echo len=${#s} 
show_bytes "$s"

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

show_string() {
  read s
  echo len=${#s}
  echo -n "$s" | od -A n -t x1
}

printf '.\001.' | show_string

printf '.\000.' | show_string

printf '\000' | show_string

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

#### Compare \x00 byte versus \x01 byte - read -n
case $SH in dash) exit ;; esac

show_string() {
  read -n 3 s
  echo len=${#s}
  echo -n "$s" | od -A n -t x1
}


printf '.\001.' | show_string

printf '.\000.' | show_string

printf '\000' | show_string

## STDOUT:
len=3
 2e 01 2e
len=2
 2e 2e
len=0
## END

## BUG-2 mksh STDOUT:
len=3
 2e 01 2e
len=1
 2e
len=0
## END

## BUG zsh STDOUT:
len=0
len=1
 2e
len=0
## END

## N-I dash STDOUT:
## END


#### Compare \x00 byte versus \x01 byte - mapfile builtin
case $SH in dash|mksh|zsh|ash) exit ;; esac

{ 
  printf '.\000.\n'
  printf '.\000.\n'
} |
{ mapfile LINES
  echo len=${#LINES[@]}
  for line in ${LINES[@]}; do
    echo -n "$line" | od -A n -t x1
  done
}

# bash is INCONSISTENT:
# - it TRUNCATES at \0, with 'mapfile'
# - rather than just IGNORING \0, with 'read'

## STDOUT:
len=2
 2e
 2e
## END

## N-I dash/mksh/zsh/ash STDOUT:
## END

#### Strip ops # ## % %% with NUL bytes

show_bytes() {
  echo -n "$1" | od -A n -t x1
}

s=$(printf '\000.\000')
echo len=${#s}
show_bytes "$s"

echo ---

t=${s#?}
echo len=${#t}
show_bytes "$t"

t=${s##?}
echo len=${#t}
show_bytes "$t"

t=${s%?}
echo len=${#t}
show_bytes "$t"

t=${s%%?}
echo len=${#t}
show_bytes "$t"

## STDOUT:
len=1
 2e
---
len=0
len=0
len=0
len=0
## END

## BUG zsh STDOUT:
len=3
 00 2e 00
---
len=2
 2e 00
len=2
 2e 00
len=2
 00 2e
len=2
 00 2e
## END

#### Issue 2269 Reduction

show_bytes() {
  echo -n "$1" | od -A n -t x1
}

s=$(printf '\000x')
echo len=${#s}
show_bytes "$s"

# strip one char from the front
s=${s#?}
echo len=${#s}
show_bytes "$s"

echo ---

s=$(printf '\001x')
echo len=${#s}
show_bytes "$s"

# strip one char from the front
s=${s#?}
echo len=${#s}
show_bytes "$s"

## STDOUT:
len=1
 78
len=0
---
len=2
 01 78
len=1
 78
## END

## BUG zsh STDOUT:
len=2
 00 78
len=1
 78
---
len=2
 01 78
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
echo escaped "$phrase"

# decode
eval "printf '%s\\n' '$phrase'"

echo ---

# harder input: NUL surrounded with ::
arg="$(printf ':\000:')" 
#echo "arg=$arg"

case $SH in
  zsh) echo 'writes binary data' ;;
  *) echo escaped "$(escape_arg "$arg")" ;;
esac
#echo "arg=$arg"

## STDOUT:
escaped that'"'"'s it!
that's it!
---
escaped ::
## END

## OK zsh STDOUT:
escaped that'"'"'s it!
that's it!
---
writes binary data
## END
