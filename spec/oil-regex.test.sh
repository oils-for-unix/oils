# Test out Oil's regular expression syntax.

#### /^.$/
shopt -s all:oil
var pat = /^.$/
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
