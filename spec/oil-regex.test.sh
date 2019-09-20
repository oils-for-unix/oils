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

