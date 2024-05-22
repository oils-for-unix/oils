## oils_failures_allowed: 0
## compare_shells: bash mksh zsh

#### OSH source code doesn't have to be valid Unicode (like other shells)

# Should YSH be different?  It would be nice.
# We would have to validate all Lit_Chars tokens, and the like.
#
# The logical place to put that would be in osh/word_parse.py where we read
# single and double quoted strings.  Although there might be a global lexer
# hack for Id.Lit_Chars tokens.  Would that catch here docs though?

# Test all the lexing contexts
cat >unicode.sh << 'EOF'
echo μ 'μ' "μ" $'μ'
EOF

# Show that all lexer modes recognize unicode sequences
#
# Oh I guess we need to check here docs too?

#$SH -n unicode.sh

$SH unicode.sh

# Trim off the first byte of mu
sed 's/\xce//g' unicode.sh > not-unicode.sh

echo --
$SH not-unicode.sh | od -A n -t x1

## STDOUT:
μ μ μ μ
--
 bc 20 bc 20 bc 20 bc 0a
## END


# dash and ash don't support $''

#### Unicode escapes \u03bc \U000003bc in $'', echo -e, printf

case $SH in dash|ash) exit ;; esac

echo $'\u03bc \U000003bc'

echo -e '\u03bc \U000003bc'

printf '\u03bc \U000003bc\n'

## STDOUT:
μ μ
μ μ
μ μ
## END

## N-I dash/ash STDOUT:
## END

#### Max code point U+10ffff can escaped with $''  printf  echo -e

case $SH in dash|ash) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

py-repr $'\U0010ffff'
py-repr $(echo -e '\U0010ffff')
py-repr $(printf '\U0010ffff')

## STDOUT:
'\xf4\x8f\xbf\xbf'
'\xf4\x8f\xbf\xbf'
'\xf4\x8f\xbf\xbf'
## END

## N-I dash/ash STDOUT:
## END

# Unicode replacement char 

## BUG mksh STDOUT:
'\xef\xbf\xbd'
'\xef\xbf\xbd'
'\xf4\x8f\xbf\xbf'
## END

#### $'' checks that 0x110000 is too big at parse time

case $SH in dash|ash|mksh) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

py-repr $'\U00110000'

## status: 2
## STDOUT:
## END

## BUG dash/ash/mksh status: 0

## BUG bash/zsh status: 0
## BUG bash/zsh STDOUT:
'\xf4\x90\x80\x80'
## END

#### $'' checks for surrogate range at parse time

case $SH in mksh) exit ;; esac

$SH << 'EOF'
x=$'\udc00'
EOF
if test $? -ne 0; then
  echo pass
else
  echo fail
fi

$SH << 'EOF'
x=$'\U0000dc00'
EOF
if test $? -ne 0; then
  echo pass
else
  echo fail
fi


## STDOUT:
pass
pass
## END

## BUG bash STDOUT:
fail
fail
## END

## BUG mksh STDOUT:
## END


#### printf / echo -e do NOT check max code point at runtime
case $SH in mksh) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

e="$(echo -e '\U00110000')"
echo status=$?
py-repr "$e"

p="$(printf '\U00110000')"
echo status=$?
py-repr "$p"

## STDOUT:
status=0
'\xf4\x90\x80\x80'
status=0
'\xf4\x90\x80\x80'
## END

## BUG mksh STDOUT:
## END

#### printf / echo -e do NOT check surrogates at runtime
case $SH in mksh) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

e="$(echo -e '\udc00')"
echo status=$?
py-repr "$e"

e="$(echo -e '\U0000dc00')"
echo status=$?
py-repr "$e"

p="$(printf '\udc00')"
echo status=$?
py-repr "$p"

p="$(printf '\U0000dc00')"
echo status=$?
py-repr "$p"

## STDOUT:
status=0
'\xed\xb0\x80'
status=0
'\xed\xb0\x80'
status=0
'\xed\xb0\x80'
status=0
'\xed\xb0\x80'
## END

## BUG zsh STDOUT:
status=0
''
status=0
''
status=0
''
status=0
''
## END

## BUG mksh STDOUT:
## END
