# spec/ysh-methods

## our_shell: ysh

#### => operator for pure computation is allowed (may be mandatory later)

# later we may make it mandatory

if ("abc" => startsWith("a")) {
  echo yes
}

var mylist = [1, 2, 3]

# This one should be ->
call mylist->pop()
echo 'ok'

## STDOUT:
yes
ok
## END

#### => can be used to chain free functions

func dictfunc() {
  return ({k1: 'spam', k2: 'eggs'})
}

echo $[list(dictfunc()) => join('/') => upper()]

# This is nicer and more consistent
echo $[dictfunc() => list() => join('/') => upper()]

## STDOUT:
K1/K2
K1/K2
## END

#### Str => startsWith()
pp line ("abc" => startsWith(""))
pp line ("abc" => startsWith("a"))
pp line ("abc" => startsWith("z"))
## status: 0
## STDOUT:
(Bool)   true
(Bool)   true
(Bool)   false
## END

#### Str => startsWith(), no args
= "abc" => startsWith()
## status: 3

#### Str => startsWith(), too many args
= "abc" => startsWith("extra", "arg")
## status: 3

#### Str => trim()
echo $["" => trim()]
echo $["  " => trim()]
echo $["mystr" => trim()]
echo $["  mystr" => trim()]
echo $["mystr  " => trim()]
echo $["  mystr  " => trim()]
echo $["  my str  " => trim()]
## STDOUT:


mystr
mystr
mystr
mystr
my str
## END

#### Str => trimLeft()
echo $["" => trimLeft()]
echo $["  " => trimLeft()]
echo $["mystr" => trimLeft()]
echo $["  mystr" => trimLeft()]
echo $["mystr  " => trimLeft()]
echo $["  mystr  " => trimLeft()]
echo $["  my str  " => trimLeft()]
## STDOUT:


mystr
mystr
mystr  
mystr  
my str  
## END

#### Str => trimRight()
echo $["" => trimRight()]
echo $["  " => trimRight()]
echo $["mystr" => trimRight()]
echo $["  mystr" => trimRight()]
echo $["mystr  " => trimRight()]
echo $["  mystr  " => trimRight()]
echo $["  my str  " => trimRight()]
## STDOUT:


mystr
  mystr
mystr
  mystr
  my str
## END

#### Str => trim*(), too many args
try { call "mystr" => trim("extra", "args") }
echo status=$_status

try { call "mystr" => trimLeft("extra", "args") }
echo status=$_status

try { call "mystr" => trimRight("extra", "args") }
echo status=$_status
## STDOUT:
status=3
status=3
status=3
## END


#### Str => trim*(), unicode aware

# u'\u0020' will crash!

# From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar#white_space
var spaces = [
  b'\u{0009}',  # Horizontal tab (\t)
  b'\u{000B}',  # Vertical tab (\v)
  b'\u{000C}',  # Form feed (\f)
  b'\u{0020}',  # Normal space
  b'\u{00A0}',  # No-break space 	<NBSP>
  b'\u{FEFF}',  # Zero-width no-break space <ZWNBSP>
] => join('')

echo $["$spaces YSH $spaces" => trim()]
## STDOUT:
YSH
## END

#### Str => trim(), unicode decoding errors
var badUtf = b'\yF9'

echo trim

# We only decode UTF until the first non-space char. So the bad UTF-8 is
# missed.
try { call " a$[badUtf]b " => trim() }
echo status=$_status

# These require trim to decode the badUtf, so an error is raised
try { call "$[badUtf]b " => trim() }
echo status=$_status
try { call " a$[badUtf]" => trim() }
echo status=$_status

# Similarly, trim{Left,Right} will assume correct encoding until shown
# otherwise.
echo trimLeft
try { call " a$[badUtf]" => trimLeft() }
echo status=$_status
try { call "$[badUtf]b " => trimLeft() }
echo status=$_status

echo trimRight
try { call "$[badUtf]b " => trimRight() }
echo status=$_status
try { call " a$[badUtf]" => trimRight() }
echo status=$_status

## STDOUT:
trim
status=0
status=3
status=3
trimLeft
status=0
status=3
trimRight
status=0
status=3
## END

#### Missing method (Str->doesNotExist())
= "abc"->doesNotExist()
## status: 3

#### Dict => keys()
var en2fr = {}
setvar en2fr["hello"] = "bonjour"
setvar en2fr["friend"] = "ami"
setvar en2fr["cat"] = "chat"
pp line (en2fr => keys())
## status: 0
## STDOUT:
(List)   ["hello","friend","cat"]
## END

#### Dict => values()
var en2fr = {}
setvar en2fr["hello"] = "bonjour"
setvar en2fr["friend"] = "ami"
setvar en2fr["cat"] = "chat"
pp line (en2fr => values())
## status: 0
## STDOUT:
(List)   ["bonjour","ami","chat"]
## END

#### Separation of -> attr and () calling
const check = "abc" => startsWith
pp line (check("a"))
## status: 0
## STDOUT:
(Bool)   true
## END

#### Bound methods, receiver value/reference semantics
var is_a_ref = { "foo": "bar" }
const f = is_a_ref => keys
pp line (f())
setvar is_a_ref["baz"] = 42
pp line (f())

var is_a_val = "abc"
const g = is_a_val => startsWith
pp line (g("a"))
setvar is_a_val = "xyz"
pp line (g("a"))
## status: 0
## STDOUT:
(List)   ["foo"]
(List)   ["foo","baz"]
(Bool)   true
(Bool)   true
## END

#### List => indexOf()
var items = [1, '2', 3, { 'a': 5 }]

json write (items => indexOf('a'))
json write (items => indexOf(1))
json write (items => indexOf('2'))
json write (items => indexOf({'a': 5}))
## STDOUT:
-1
0
1
3
## END

#### List => join()
var items = [1, 2, 3]

json write (items => join())  # default separator is ''
json write (items => join(" "))  # explicit separator (can be any number or chars)
json write (items => join(", "))  #  separator can be any number of chars

try {
  json write (items => join(1))  # separator must be a string
}
echo "failed with status $_status"
## STDOUT:
"123"
"1 2 3"
"1, 2, 3"
failed with status 3
## END

#### List->reverse()

var empty = []

var a = [0]
var b = [2, 1, 3]
var c = :| hello world |

call empty->reverse()
call a->reverse()
call b->reverse()
call c->reverse()

json write --pretty=F (empty)
json write --pretty=F (a)
json write --pretty=F (b)
json write --pretty=F (c)

## STDOUT:
[]
[0]
[3,1,2]
["world","hello"]
## END

#### List->reverse() from iterator
var x = list(0 .. 3)
call x->reverse()
write @x
## STDOUT:
2
1
0
## END

