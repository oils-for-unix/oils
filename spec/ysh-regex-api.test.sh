## oils_failures_allowed: 0

#### s ~ regex and s !~ regex
shopt -s ysh:upgrade

var s = 'foo'
if (s ~ '.([[:alpha:]]+)') {  # ERE syntax
  echo matches
  argv.py $[_group(0)] $[_group(1)]
}
if (s !~ '[[:digit:]]+') {
  echo "does not match"
  argv.py $[_group(0)] $[_group(1)]
}

if (s ~ '[[:digit:]]+') {
  echo "matches"
}
# Should be cleared now
# should this be Undef rather than ''?
try {
  var x = _group(0)
}
if (_status === 3) {
  echo 'got expected status 3'
}

try {
  var y = _group(1)
}
if (_status === 3) {
  echo 'got expected status 3'
}

## STDOUT:
matches
['foo', 'oo']
does not match
['foo', 'oo']
got expected status 3
got expected status 3
## END

#### Invalid regex has libc error message

shopt -s ysh:upgrade

# Hm it's hard to test this, we can't get stderr of YSH from within YSH?
#fopen 2>err.txt {
#  if ('abc' ~ '+') {
#    echo 'bad'
#  }
#}

if ('abc' ~ '+') {
  echo 'bad'
}

## status: 2
## STDOUT:
## END

#### Eggex flags to ignore case are respected
shopt -s ysh:upgrade

# based on Python's spelling
var pat = / 'abc' ; i /
var pat2 = / @pat 'def' ; reg_icase /  # this is allowed

if ('-abcdef-' ~ pat2) {
  echo 'yes'
}

if ('-ABCDEF-' ~ pat2) {
  echo 'yes'
}

if ('ABCDE' ~ pat2) {
  echo 'BUG'
}

## STDOUT:
yes
yes
## END

#### Positional captures with _group
shopt -s ysh:all

var x = 'zz 2020-08-20'

if [[ $x =~ ([[:digit:]]+)-([[:digit:]]+) ]] {
  argv.py "${BASH_REMATCH[@]}"
}

# THIS IS A NO-OP.  The variable is SHADOWED by the special name.
# I think that's OK.
setvar BASH_REMATCH = :| reset |

if (x ~ /<capture d+> '-' <capture d+>/) {
  argv.py "${BASH_REMATCH[@]}"
  argv.py $[_group(0)] $[_group(1)] $[_group(2)]

  # TODO: Also test _start() and _end()
}
## STDOUT:
['2020-08', '2020', '08']
['2020-08', '2020', '08']
['2020-08', '2020', '08']
## END

#### _group() returns null when group doesn't match
shopt -s ysh:upgrade

var pat = / <capture 'a'> | <capture 'b'> /
if ('b' ~ pat) {
  echo "$[_group(1)] $[_group(2)]"
}
## STDOUT:
null b
## END

#### _start() and _end()
shopt -s ysh:upgrade

var s = 'foo123bar'
if (s ~ /digit+/) {
  echo start=$[_start(0)] end=$[_end(0)]
}
echo ---

if (s ~ / <capture [a-z]+> <capture digit+> /) {
  echo start=$[_start(1)] end=$[_end(1)]
  echo start=$[_start(2)] end=$[_end(2)]
}
echo ---

if (s ~ / <capture [a-z]+> | <capture digit+> /) {
  echo start=$[_start(1)] end=$[_end(1)]
  echo start=$[_start(2)] end=$[_end(2)]
}

## STDOUT:
start=3 end=6
---
start=0 end=3
start=3 end=6
---
start=0 end=3
start=-1 end=-1
## END

#### Str->search() method returns value.Match object

var s = '= Hi5- Bye6-'

var m = s => search(/ <capture [a-z]+ > <capture d+> '-' ; i /)
echo "g0 $[m => start(0)] $[m => end(0)] $[m => group(0)]"
echo "g1 $[m => start(1)] $[m => end(1)] $[m => group(1)]"
echo "g2 $[m => start(2)] $[m => end(2)] $[m => group(2)]"

echo ---

var pos = m => end(0)  # search from end position
var m = s => search(/ <capture [a-z]+ > <capture d+> '-' ; i /, pos=pos)
echo "g0 $[m => start(0)] $[m => end(0)] $[m => group(0)]"
echo "g1 $[m => start(1)] $[m => end(1)] $[m => group(1)]"
echo "g2 $[m => start(2)] $[m => end(2)] $[m => group(2)]"

## STDOUT:
g0 2 6 Hi5-
g1 2 4 Hi
g2 4 5 5
---
g0 7 12 Bye6-
g1 7 10 Bye
g2 10 11 6
## END

#### Str->search() only matches %start ^ when pos == 0

shopt -s ysh:upgrade

var anchored = / %start <capture d+> '-' /
var free = / <capture d+> '-' /

var s = '12-34-'

for pat in ([anchored, free]) {
  echo "pat=$pat"

  var pos = 0
  while (true) {
    var m = s => search(pat, pos=pos)
    if (not m) {
      break
    }
    echo $[m => group(0)]
    setvar pos = m => end(0)
  }

}

## STDOUT:
pat=^([[:digit:]]+)-
12-
pat=([[:digit:]]+)-
12-
34-
## END


#### search() and leftMatch() accept ERE string

var s = '= hi5- bye6-'

var m = s => search('([[:alpha:]]+)([[:digit:]]+)-')
echo "g0 $[m => start(0)] $[m => end(0)] $[m => group(0)]"
echo "g1 $[m => start(1)] $[m => end(1)] $[m => group(1)]"
echo "g2 $[m => start(2)] $[m => end(2)] $[m => group(2)]"
echo ---

var m = s[2:] => leftMatch('([[:alpha:]]+)([[:digit:]]+)-')
echo "g0 $[m => start(0)] $[m => end(0)] $[m => group(0)]"
echo "g1 $[m => start(1)] $[m => end(1)] $[m => group(1)]"
echo "g2 $[m => start(2)] $[m => end(2)] $[m => group(2)]"

## STDOUT:
g0 2 6 hi5-
g1 2 4 hi
g2 4 5 5
---
g0 0 4 hi5-
g1 0 2 hi
g2 2 3 5
## END

#### Str->leftMatch() can implement lexer pattern

shopt -s ysh:upgrade

var lexer = / <capture d+> | <capture [a-z]+> | <capture s+> /
#echo $lexer

proc show-tokens (s) {
  var pos = 0

  while (true) {
    echo "pos=$pos"

    var m = s->leftMatch(lexer, pos=pos)
    if (not m) {
      break
    }
    # TODO: add groups()
    #var groups = [m => group(1), m => group(2), m => group(3)]
    #json write --pretty=F (groups)
    echo "$[m => group(1)]/$[m => group(2)]/$[m => group(3)]/"

    echo

    setvar pos = m => end(0)
  }
}

show-tokens 'ab 12'

echo '==='

# There's a token here that doesn't leftMatch()
show-tokens 'ab+12'

## STDOUT:
pos=0
null/ab/null/

pos=2
null/null/ /

pos=3
12/null/null/

pos=5
===
pos=0
null/ab/null/

pos=2
## END

#### Named captures with m => group()
shopt -s ysh:all

var s = 'zz 2020-08-20'
var pat = /<capture d+ as year> '-' <capture d+ as month>/

var m = s => search(pat)
argv.py $[m => group('year')] $[m => group('month')]
echo $[m => start('year')] $[m => end('year')]
echo $[m => start('month')] $[m => end('month')]

argv.py $[m => group('oops')]
echo 'error'

## status: 3
## STDOUT:
['2020', '08']
3 7
8 10
## END

#### Named captures with _group() _start() _end()
shopt -s ysh:all

var x = 'zz 2020-08-20'

if (x ~ /<capture d+ as year> '-' <capture d+ as month>/) {
  argv.py $[_group('year')] $[_group('month')]
  echo $[_start('year')] $[_end('year')]
  echo $[_start('month')] $[_end('month')]
}

argv.py $[_group('oops')]

## status: 3
## STDOUT:
['2020', '08']
3 7
8 10
## END

#### Named Capture Decays Without Name
shopt -s ysh:all
var pat = /<capture d+ as month>/
echo $pat

if ('123' ~ pat) {
  echo yes
}

## STDOUT:
([[:digit:]]+)
yes
## END

#### Nested Named Capture Uses ( ordering

shopt -s ysh:upgrade

var Date = /<capture d+ as year> '-' <capture d+ as month>/
var Time = /<capture d+ as hour> ':' <capture d+ as minute> (':' <capture d+ as secs>)? /

var pat = / 'when: ' (<capture Date> | <capture Time as two>) /
#echo $pat

proc show-groups (; m) {
  echo 0 $[m => group(0)]
  echo 1 $[m => group(1)]  # this is everything except when
  echo 2 $[m => group(2)]
  echo
  echo $[m => group('two')]
  echo $[m => group('year')] $[m => group('month')]
  echo $[m => group('hour')] $[m => group('minute')] $[m => group('secs')]
}

var m = 'when: 2023-10' => leftMatch(pat)

show-groups (m)

var m = 'when: 23:30' => leftMatch(pat)

echo ---
show-groups (m)

var m = 'when: 23:30:59' => leftMatch(pat)

echo ---
show-groups (m)

## STDOUT:
0 when: 2023-10
1 2023-10
2 2023-10

null
2023 10
null null null
---
0 when: 23:30
1 23:30
2 null

23:30
null null
23 30 null
---
0 when: 23:30:59
1 23:30:59
2 null

23:30:59
null null
23 30 59
## END

#### Capture with Type Conversion Func
shopt -s ysh:upgrade

var s = 'hi 42-3.14'
var pat = / <capture d+: int> '-' <capture d+ '.' d+ : float> /

if (s  ~ pat) {
  var g1 = _group(1)  # Int
  var g2 = _group(2)  # Float
  echo $[type(g1)] $[type(g2)]
}

var m = s => search(pat)
if (m) {
  echo $[m => group(1) => type()] $[m => group(2) => type()]
}

## STDOUT:
Int Float
Int Float
## END


#### Named Capture with Type Conversion Func
shopt -s ysh:upgrade

func floatNegate(x) {
  return (-float(x))
}

var s = 'hi 42-3.14'
var pat = / <capture d+ as left: int> '-' <capture d+ '.' d+ as right: floatNegate> /

if (s ~ pat) {
  var g1 = _group('left')  # Int
  var g2 = _group('right')  # Float
  echo $g2
  echo $[type(g1)] $[type(g2)]
}

var m = s => search(pat)
if (m) {
  echo $[m => group('right')]
  echo $[m => group('left') => type()] $[m => group('right') => type()]
}

## STDOUT:
-3.14
Int Float
-3.14
Int Float
## END

#### Can't splice eggex with different flags
shopt -s ysh:upgrade

var pat = / 'abc' ; i /
var pat2 = / @pat 'def' ; reg_icase /  # this is allowed

var pat3 = / @pat 'def' /
= pat3

## status: 1
## STDOUT:
## END

#### Eggex with translation preference has arbitrary flags
shopt -s ysh:upgrade

# TODO: can provide introspection so users can translate it?
# This is kind of a speculative corner of the language.

var pat = / d+ ; ignorecase ; PCRE /

# This uses ERE, as a test
if ('ab 12' ~ pat) {
  echo yes
}

## STDOUT:
yes
## END


#### Invalid sh operation on eggex
var pat = / d+ /
#pat[invalid]=1
pat[invalid]+=1
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

shopt -s ysh:all

const DecDigit = / [0-9] /
const BinDigit = / [0-1] /
const OctDigit = / [0-7] /
const HexDigit = / [0-9 a-f A-F] /  # note: not splicing Digit into character class

const DecInt   = / [1-9] ('_'? DecDigit)* | '0'+ ('_'? '0')* /
const BinInt   = / '0' [b B] ('_'? BinDigit)+ /
const OctInt   = / '0' [o O] ('_'? OctDigit)+ /
const HexInt   = / '0' [x X] ('_'? HexDigit)+ /

const Integer  = / %start (DecInt | BinInt | OctInt | HexInt) %end /

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

#### Regex in a loop (bug regression)

shopt --set ysh:all

var content = [ 1, 2 ]
var i = 0
while (i < len(content)) {
  var line = content[i]
  write $[content[i]]
  if (str(line) ~ / s* 'imports' s* '=' s* .* /) {
    exit
  }
  setvar i += 1
}

## STDOUT:
1
2
## END


#### Regex in a loop depending on var

shopt --set ysh:all

var lines = ['foo', 'bar']
for line in (lines) {
  write "line $line"

  # = / $line /

if ("x$line" ~ / dot @line /) {
  #if (line ~ / $line /) {
    write "matched $line"
  }
}

## STDOUT:
line foo
matched foo
line bar
matched bar
## END


#### Regex with [ (bug regression)
shopt --set ysh:all

if ('[' ~ / '[' /) {
  echo 'sq'
}

if ('[' ~ / [ '[' ] /) {
  echo 'char class'
}

# User-reported string
if ("a" ~ / s* 'imports' s* '=' s* '[' /) {
  echo "yes"
}

## STDOUT:
sq
char class
## END

#### Str=>replace(Str, Str)
shopt --set ysh:all

var mystr = 'abca'
write $[mystr=>replace('a', 'A')]  # Two matches
write $[mystr=>replace('b', 'B')]  # One match
write $[mystr=>replace('x', 'y')]  # No matches

write $[mystr=>replace('abc', '')]  # Empty substitution
write $[mystr=>replace('', 'new')]  # Empty substring
## STDOUT:
AbcA
aBca
abca
a
newanewbnewcnewanew
## END

#### Str=>replace(Eggex, Str)
shopt --set ysh:all

var mystr = 'mangled----kebab--case'
write $[mystr=>replace(/ '-'+ /, '-')]

setvar mystr = 'smaller-to-bigger'
write $[mystr=>replace(/ '-'+ /, '---')]
## STDOUT:
mangled-kebab-case
smaller---to---bigger
## END

#### Str=>replace(Eggex, Expr)
shopt --set ysh:all

var mystr = 'name: Bob'
write $[mystr=>replace(/ 'name: ' <capture dot+> /, ^"Hello $1")]
## STDOUT:
Hello Bob
## END

#### Str=>replace(Eggex, Expr), scopes
shopt --set ysh:all

var mystr = '123'

var anotherVar = 'surprise!'
write $[mystr=>replace(/ <capture d+> /, ^"Hello $1 ($anotherVar)")]

var globalName = '456'
write $[mystr=>replace(/ <capture d+ as globalName> /, ^"Hello $globalName")]

write $[mystr=>replace(/ <capture d+ as localName> /, ^"Hello $localName, $globalName")]
## STDOUT:
Hello 123 (surprise!)
Hello 123
Hello 123, 456
## END

#### Str=>replace(Eggex, *, count)
shopt --set ysh:all

var mystr = '1abc2abc3abc'

for count in (0..4) {
  write $[mystr=>replace('abc', "-", count=count)]
  write $[mystr=>replace('abc', ^"-", count=count)]
  write $[mystr=>replace(/ [a-z]+ /, "-", count=count)]
  write $[mystr=>replace(/ [a-z]+ /, "-", count=count)]
}
## STDOUT:
1-2-3-
1-2-3-
1-2-3-
1-2-3-
1-2abc3abc
1-2abc3abc
1-2abc3abc
1-2abc3abc
1-2-3abc
1-2-3abc
1-2-3abc
1-2-3abc
1-2-3-
1-2-3-
1-2-3-
1-2-3-
## END

#### Str=>replace(Eggex, Lazy), convert_func
shopt --set ysh:all

var mystr = '123'

write $[mystr=>replace(/ <capture d+ as n : int> /, ^"$[n + 1]")]

# values automatically get stringified
write $[mystr=>replace(/ <capture d+ as n : int> /, ^"$1")]

func not_str(inp) {
  return ({ "value": inp })
}

# should fail to stringify $1
try { call mystr=>replace(/ <capture d+ : not_str> /, ^"$1") }
write status=$_status
## STDOUT:
124
123
status=3
## END
