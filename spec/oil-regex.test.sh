# Test out Oil's regular expression syntax.

#### /^.$/
shopt -s oil:all
var pat = ''

setvar pat = /^.$/
echo pat=$pat

setvar pat = /%start dot %end/
echo pat=$pat

if ('' ~ pat) {  # ERE syntax
  echo yes
} else {
  echo no
}
# $pat is same as pat
if ('f' ~ pat) {  # ERE syntax
  echo yes
} else {
  echo no
}

## STDOUT:
pat=^.$
pat=^.$
no
yes
## END


#### /.+/
shopt -s oil:all

var pat = /.+/
echo $pat

var s = 'foo'
if (s ~ pat) {  # ERE syntax
  echo yes
}
var empty = ''
if (empty ~ pat) { echo yes } else { echo no }
## STDOUT:
.+
yes
no
## END

#### Repeat {1,3} etc.
var pat = null

setvar pat = /d{2}/
echo $pat
setvar pat = /d{1,3}/
echo $pat
setvar pat = /d{1,}/
echo $pat
setvar pat = /d{,3}/
echo $pat


## STDOUT:
[[:digit:]]{2}
[[:digit:]]{1,3}
[[:digit:]]{1,}
[[:digit:]]{,3}
## END


#### d+  digit+  ~d+  ~digit+
shopt -s oil:all

var pat = ''

setvar pat = /d+/
echo $pat
if ('42' ~ pat) { echo yes }

var empty = ''
if (empty ~ pat) { echo yes } else { echo no }

setvar pat = /digit+/
echo $pat
setvar pat = /~d+/
echo $pat
setvar pat = /~digit+/
echo $pat


## STDOUT:
[[:digit:]]+
yes
no
[[:digit:]]+
[^[:digit:]]+
[^[:digit:]]+
## END

#### Alternation and sequence
var pat = ''
setvar pat = /s d+ | w*/
echo $pat
setvar pat = /s d+ or w*/
echo $pat
## STDOUT:
[[:space:]][[:digit:]]+|[[:alpha:][:digit:]_]*
[[:space:]][[:digit:]]+|[[:alpha:][:digit:]_]*
## END

#### Char Class Ranges
shopt -s oil:all

var pat = ''
setvar pat = /[0-9 a-f]+/
echo $pat
# This is equivalent
setvar pat = /['0' - '9' 'a' - 'f']+/
echo $pat

if ('0123' ~ pat) { echo yes } else { echo no }
if ('zzz' ~ pat) { echo yes } else { echo no }
if ('' ~ pat) { echo yes } else { echo no }
## STDOUT:
[0-9a-f]+
[0-9a-f]+
yes
no
no
## END

#### Char Class Set
shopt -s oil:all
var pat = ''

# This is NOT allowed
# setvar pat = /[a b c]+/

setvar pat = /['abc']+/
echo $pat

if ('cbcb' ~ pat) { echo yes } else { echo no }
if ('0123' ~ pat) { echo yes } else { echo no }
if ('' ~ pat) { echo yes } else { echo no }
## STDOUT:
[abc]+
yes
no
no
## END

#### Range with escaped characters
shopt -s oil:all

var pat = null

setvar pat = / [ \x00 - \x0f ] /
echo $pat | od -A n -t x1

## STDOUT:
 5b 00 2d 0f 5d 0a
## END


#### Group ()
shopt -s oil:all
var pat = ''

setvar pat = /(%start s or d d)/
echo $pat

if (' foo' ~ pat) { echo yes } else { echo no }
if ('-00-' ~ pat) { echo yes } else { echo no }
if ('foo' ~ pat) { echo yes } else { echo no }

## STDOUT:
(^[[:space:]]|[[:digit:]][[:digit:]])
yes
yes
no
## END

#### Capture is acceptable as a group
shopt -s oil:all
var pat = /<%start s | d d>/
echo $pat
## STDOUT:
(^[[:space:]]|[[:digit:]][[:digit:]])
## END

#### Named Capture Decays Without Name
shopt -s oil:all
var pat = /<d+ : month>/
echo $pat

if ('123' ~ pat) {
  echo yes
}

## STDOUT:
([[:digit:]]+)
yes
## END

#### Named Capture With ~ Assigns Variable
shopt -s oil:all
var pat = /<d+ : month>/
echo $pat

if ('123' ~ pat) {
  echo yes
  = month
}
## STDOUT:
([[:digit:]]+)
yes
TODO MONTH
## END

#### literal ''
shopt -s oil:all
var pat = ''

setvar pat = /'abc' 'def'/
echo $pat

#setvar pat = /'abc' '^ + * ?'/
#echo $pat

if ('abcde' ~ pat) { echo yes } else { echo no }
if ('abcdef' ~ pat) { echo yes } else { echo no }

## STDOUT:
abcdef
no
yes
## END

#### double quoted, $x, and ${x}
shopt -s oil:all
var pat = ''

var x = 'x'
var y = 'y'
setvar pat = / $x ${x} "abc" "$x${y}"/
echo $pat

if ('xxabcx' ~ pat) { echo yes } else { echo no }
if ('xxabcxyf' ~ pat) { echo yes } else { echo no }

## STDOUT:
xxabcxy
no
yes
## END

#### @splice
shopt -s oil:all
var d = /d+/;
var ip = / @d '.' @d '.' @d '.' @d /
echo $ip
if ('0.0.0.0' ~ ip) { echo yes } else { echo no }
if ('0.0.0' ~ ip) { echo yes } else { echo no }
## STDOUT:
[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+
yes
no
## END

#### splice with capital letters
shopt -s oil:all
var D = /d+/;
var ip = / D '.' D '.' D '.' D /
echo $ip
if ('0.0.0.0' ~ ip) { echo yes } else { echo no }
if ('0.0.0' ~ ip) { echo yes } else { echo no }
## STDOUT:
[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+
yes
no
## END

#### Matching escaped tab character
shopt -s oil:all

# BUG: need C strings in array literal
var lines=@($'aa\tbb' $'cc\tdd')

var pat = / ('a' [\t] 'b') /
write pat=$pat
write @lines | egrep $pat 

## stdout-json: "pat=(a[\t]b)\naa\tbb\n"

#### Match non-ASCII byte denoted using c'\xff'
shopt -s oil:all
var pat = /[ c'\xff' ]/;

echo $pat | od -A n -t x1
if (c'\xff' ~ pat) { echo yes } else { echo no }
if (c'\xfe' ~ pat) { echo yes } else { echo no }

## STDOUT:
 5b ff 5d 0a
yes
no
## END

#### Match non-ASCII byte denoted using \xff
shopt -s oil:all
var pat = /[ \xff ]/;

echo $pat | od -A n -t x1
if (c'\xff' ~ pat) { echo yes } else { echo no }
if (c'\xfe' ~ pat) { echo yes } else { echo no }

## STDOUT:
 5b ff 5d 0a
yes
no
## END

#### ERE can express Unicode escapes that are in the ASCII range
shopt -s oil:all
var pat = /[ \u007f ]/;

echo $pat | od -A n -t x1
if (c'\x7f' ~ pat) { echo yes } else { echo no }
if (c'\x7e' ~ pat) { echo yes } else { echo no }

## STDOUT:
 5b 7f 5d 0a
yes
no
## END

#### ERE can't express higher Unicode escapes
shopt -s oil:all
var pat = /[ \u00ff ]/;

echo $pat | od -A n -t x1
if (c'\x7f' ~ pat) { echo yes } else { echo no }
if (c'\x7e' ~ pat) { echo yes } else { echo no }

## status: 1
## stdout-json: ""

#### non-ASCII bytes must be singleton terms, e.g. '\x7f\xff' is disallowed
var bytes = c'\x7f\xff'
var pat = / [ $bytes ] /
echo $pat
## status: 1
## stdout-json: ""

#### Matching escaped tab character
shopt -s oil:all

# BUG: need C strings in array literal
var lines=@($'aa\tbb' $'cc\tdd')

var pat = / ('a' [\t] 'b') /
write pat=$pat
write @lines | egrep $pat 

## stdout-json: "pat=(a[\t]b)\naa\tbb\n"

#### Matching ] and \ and ' and " in character classes
shopt -s oil:all

# BUG: need C strings in array literal
var lines=@(
  'backslash \'
  'rbracket ]'
  'lbracket ['
  "sq '"
  'dq "'
)

# Weird GNU quirk: ] has to come first!
# []abc] works.  But [abc\]] does NOT work.  Stupid rule!

var pat = / [ ']' \\ \' \" ] /
write pat=$pat
write @lines | egrep $pat 

## STDOUT:
pat=[]\\'"]
backslash \
rbracket ]
sq '
dq "
## END

#### Matching literal hyphen in character classes
shopt -s oil:all

var literal = '-'
var pat = / [ 'a' $literal 'b' ${literal} "-" ] /
write pat=$pat
write 'c-d' 'ab' 'cd' | grep $pat
## STDOUT:
pat=[a\-b\-\-]
c-d
ab
## END

#### Repeated String Literal With Single Char
shopt -s oil:all

var literal = 'f'
var pat = null

setvar pat = / %start $literal+ %end /
echo $pat
setvar pat = / %start ($literal)+ %end /
echo $pat

if ('fff' ~ pat) { echo yes }
if ('foo' !~ pat) { echo no }

## STDOUT:
^f+$
^(f)+$
yes
no
## END

#### Error when unparenthesized string of more than one character is repeated
shopt -s oil:all

var literal = 'foo'
var pat = null

setvar pat = / %start $literal+ %end /
echo $pat
setvar pat = / %start ($literal)+ %end /
echo $pat

if ('foofoo' ~ pat) { echo yes }
if ('foof' !~ pat) { echo no }

## status: 1
## stdout-json: ""

#### Instead of c'foo\\bar' use 'foo' \\ 'bar'
shopt -s oil:all
var pat = /'foo' \\ 'bar'/
echo $pat

if (r'foo\bar' ~ pat) { echo yes }
if (r'foo.bar' !~ pat) { echo no }
## STDOUT:
foo\\bar
yes
no
## END

#### Negation of Character Class
shopt -s oil:all

var pat = / ~[ a-z ] /
echo $pat

if ('0' ~ pat) { echo yes }
if ('a' !~ pat) { echo no }

## STDOUT:
[^a-z]
yes
no
## END

#### Posix and Perl class in class literals
shopt -s oil:all

var pat = null

setvar pat = / [ space 'z' ] /
echo $pat
#setvar pat = / [ ~space 'z' ] /
#echo $pat

# PROBLEM: can't negate individual POSIX classes.  They would have to be a Perl
# class to be \D or \S.
# [[:space:]z] negates the whole thing!
# [^[:space:]]

setvar pat = / [ digit 'z' ] /
echo $pat
#setvar pat = / [ ~digit 'z' ] /
#echo $pat

## STDOUT:
[[:space:]z]
[[:digit:]z]
## END

#### [~d] can't be negated because it's a literal character
setvar pat = / [ ~d 'z' ] /
echo $pat
## status: 2
## stdout-json: ""

#### [~digit] can't be negated in POSIX ERE (but yes in Perl)
var pat = null
setvar pat = / [ ~digit 'z' ] /
echo $pat
## status: 1
## stdout-json: ""

#### Long Python Example

# https://docs.python.org/3/reference/lexical_analysis.html#integer-literals

# integer      ::=  decinteger | bininteger | octinteger | hexinteger
# decinteger   ::=  nonzerodigit (["_"] digit)* | "0"+ (["_"] "0")*
# bininteger   ::=  "0" ("b" | "B") (["_"] bindigit)+
# octinteger   ::=  "0" ("o" | "O") (["_"] octdigit)+
# hexinteger   ::=  "0" ("x" | "X") (["_"] hexdigit)+
# nonzerodigit ::=  "1"..."9"
# digit        ::=  "0"..."9"
# bindigit     ::=  "0" | "1"
# octdigit     ::=  "0"..."7"
# hexdigit     ::=  digit | "a"..."f" | "A"..."F"

shopt -s oil:all

DecDigit = / [0-9] /
BinDigit = / [0-1] /
OctDigit = / [0-7] /
HexDigit = / [0-9 a-f A-F] /  # note: not splicing Digit into character class

DecInt   = / [1-9] ('_'? DecDigit)* | '0'+ ('_'? '0')* /
BinInt   = / '0' [b B] ('_'? BinDigit)+ /
OctInt   = / '0' [o O] ('_'? OctDigit)+ /
HexInt   = / '0' [x X] ('_'? HexDigit)+ /

Integer  = / %start (DecInt | BinInt | OctInt | HexInt) %end /

#echo $Integer

if (    '123'  ~ Integer) { echo 'Y' }
if (    'zzz' !~ Integer) { echo 'N' }

if ('123_000'  ~ Integer) { echo 'Y decimal' }
if ('000_123' !~ Integer) { echo 'N decimal' }

if (  '0b100'  ~ Integer) { echo 'Y binary' }
if (  '0b102' !~ Integer) { echo 'N binary' }

if (  '0o755'  ~ Integer) { echo 'Y octal' }
if (  '0o778' !~ Integer) { echo 'N octal' }

if (   '0xFF'  ~ Integer) { echo 'Y hex' }
if (   '0xFG' !~ Integer) { echo 'N hex' }

## STDOUT:
Y
N
Y decimal
N decimal
Y binary
N binary
Y octal
N octal
Y hex
N hex
## END
