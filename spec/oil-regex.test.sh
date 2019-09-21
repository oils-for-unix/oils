# Test out Oil's regular expression syntax.

#### /^.$/
shopt -s all:oil
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
shopt -s all:oil

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
shopt -s all:oil

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
shopt -s all:oil

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
shopt -s all:oil
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

#### Group ()
shopt -s all:oil
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


#### literal ''
shopt -s all:oil
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
shopt -s all:oil
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
shopt -s all:oil
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

#### Matching escaped tab character
shopt -s all:oil

# BUG: need C strings in array literal
var lines=@($'aa\tbb' $'cc\tdd')

var pat = / ('a' [\t] 'b') /
echo pat=$pat
echo @lines | egrep $pat 

## stdout-json: "pat=(a[\t]b)\naa\tbb\n"

#### Matching ] and \ and ' and " in character classes
shopt -s all:oil

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
echo pat=$pat
echo @lines | egrep $pat 

## STDOUT:
pat=[]\\'"]
backslash \
rbracket ]
sq '
dq "
## END

#### Matching literal hyphen in character classes
shopt -s all:oil

var literal = '-'
var pat = / [ 'a' $literal 'b' ${literal} "-" ] /
echo pat=$pat
echo 'c-d' 'ab' 'cd' | grep $pat
## STDOUT:
pat=[a\-b\-\-]
c-d
ab
## END

