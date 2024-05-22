## oils_failures_allowed: 5

#### ${#s} and len(s)

source $REPO_ROOT/spec/testdata/unicode.sh

# bash agrees
echo "farmer scalars =" ${#farmer}

echo "facepalm scalars =" ${#facepalm}

echo "farmer len =" $[len(farmer)]

echo "facepalm len =" $[len(facepalm)]

## STDOUT:
farmer scalars = 4
facepalm scalars = 5
farmer len = 15
facepalm len = 17
## END


#### Encoded value above max code point

# Python DOES check this

max=$(python2 -c 'print u"\U0010ffff".encode("utf-8")')
echo status max=$?

too_big=$(python2 -c 'print u"\U00110000".encode("utf-8")')
echo status too_big=$?

echo py max=$max
echo py too_big=$too_big

python2 -c 'import sys; c = sys.argv[1].decode("utf-8"); print len(c)' "$ok"
#python2 -c 'import sys; c = sys.argv[1].decode("utf-8"); print len(c)' "$too_big"

var max = u'\u{10ffff}'
var too_big = u'\u{110000}'

echo ysh max=$max
# BUG
echo ysh too_big=$too_big

# These are errors too
var max = b'\u{10ffff}'
var too_big = b'\u{110000}'

## STDOUT:
status max=0
status too_big=1
## END


#### JSON \uXXXX\uYYYY above max code point

echo

## STDOUT:
## END

#### J8 \u{123456} above max code point

echo

## STDOUT:
## END

#### YSH source code rejects encoded string above max code point

max=$(bash <<'EOF'
echo $'\U0010ffff'
EOF
)

# bash allows the bad one
too_big=$(bash <<'EOF'
echo $'\U00110000'
EOF
)

echo "var x = u'"$max"'; = x" | $SH
echo status=$?
#pp line (_reply)

echo "var x = u'"$too_big"'; = x" | $SH
echo status=$?
#pp line (_reply)

## STDOUT:
## END


#### JSON and J8 reject encoded string above max code point

max=$(bash <<'EOF'
echo $'\U0010ffff'
EOF
)

# bash allows the bad one
too_big=$(bash <<'EOF'
echo $'\U00110000'
EOF
)

# JSON string

echo '"'$max'"' | json read
echo status=$?
#pp line (_reply)

# Need to propagate the reason here

echo '"'$too_big'"' | json read
echo status=$?
#pp line (_reply)


# J8 string

echo "u'"$max"'" | json8 read
echo status=$?
#pp line (_reply)

echo "u'"$too_big"'" | json8 read
echo status=$?
#pp line (_reply)

## STDOUT:
status=0
status=1
status=0
status=1
## END

#### = keyword on max code point

var max = u'\u{10ffff}'

json write (max)
json8 write (max)

#= max

#echo "var x = u'"$max"'; = x" | $SH

## STDOUT:
## END
