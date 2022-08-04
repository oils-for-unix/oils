# spec/nul-bytes

#### NUL bytes with echo -e
case $SH in (dash) exit ;; esac

echo -e '\0'
## stdout-repr: "\x00\n"
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
