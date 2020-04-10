# Cross-cutting test of serialization formats.  That is, what QSTR should fix.
#
# TODO: Also see spec/xtrace for another use case.

#### printf %q newline
case $SH in (ash) return ;; esac  # yash and ash don't implement this

newline=$'one\ntwo'
printf '%q\n' "$newline"

quoted="$(printf '%q\n' "$newline")"
restored=$(eval "echo $quoted")
test "$newline" = "$restored" && echo roundtrip-ok

## STDOUT:
$'one\ntwo'
roundtrip-ok
## END
## OK mksh STDOUT:
'one'$'\n''two'
roundtrip-ok
## END
## OK zsh STDOUT:
one$'\n'two
roundtrip-ok
## END
## N-I ash stdout-json: ""

#### printf %q spaces
case $SH in (ash) return ;; esac  # yash and ash don't implement this

# bash does a weird thing and uses \

spaces='one two'
printf '%q\n' "$spaces"

## STDOUT:
'one two'
## END
## OK bash/zsh STDOUT:
one\ two
## END
## N-I ash stdout-json: ""

#### printf %q quotes
case $SH in (ash) return ;; esac  # yash and ash don't implement %q

quotes=\'\"
printf '%q\n' "$quotes"

quoted="$(printf '%q\n' "$quotes")"
restored=$(eval "echo $quoted")
test "$quotes" = "$restored" && echo roundtrip-ok

## STDOUT:
\'\"
roundtrip-ok
## END
## OK osh STDOUT:
$'\'"'
roundtrip-ok
## END
## BUG mksh STDOUT:
''\''"'
roundtrip-ok
## END
## N-I ash stdout-json: ""

#### printf %q unprintable
case $SH in (ash) return ;; esac  # yash and ash don't implement this

unprintable=$'\xff'
printf '%q\n' "$unprintable"

# Oil issue: we are passing BIT8_RAW, so we get it literally.
## STDOUT:
$'\377'
## END
## BUG mksh STDOUT:
''$'\377'
## END
## N-I ash stdout-json: ""

#### printf %q unicode
case $SH in (ash) return ;; esac  # yash and ash don't implement this

unicode=$'\u03bc'
printf '%q\n' "$unicode"

# Oil issue: we have quotes.  Isn't that OK?
## STDOUT:
μ
## END
## N-I ash stdout-json: ""


#### set
case $SH in (zsh) return ;; esac  # zsh doesn't make much sense

zz=$'one\ntwo'

set | grep zz
## STDOUT:
zz=$'one\ntwo'
## END
## OK ash stdout-json: "zz='one\n"
## BUG zsh stdout-json: ""


#### declare
case $SH in (ash|zsh) return ;; esac  # zsh doesn't make much sense

zz=$'one\ntwo'

typeset | grep zz
typeset -p zz

# bash uses a different format for 'declare' and 'declare -p'!

## STDOUT:
zz=$'one\ntwo'
declare -- zz="one
two"
## END
## OK mksh STDOUT:
typeset zz
typeset zz=$'one\ntwo'
## BUG zsh stdout-json: ""
## N-I ash stdout-json: ""

#### ${var@Q}
case $SH in (zsh|ash) exit ;; esac

zz=$'one\ntwo'
echo ${zz@Q}
## STDOUT:
$'one\ntwo'
## END
## OK mksh STDOUT:
$'one
two'
## END
## N-I ash/zsh stdout-json: ""
