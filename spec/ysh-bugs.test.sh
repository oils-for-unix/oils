## our_shell: ysh
## oils_failures_allowed: 3

#### fastlex: NUL byte not allowed inside char literal #' '

echo $'var x = #\'\x00\'; echo x=$x' > tmp.oil
$SH tmp.oil

echo $'var x = #\' ' > incomplete.oil
$SH incomplete.oil

## status: 2
## STDOUT:
## END

#### fastlex: NUL byte inside shebang line

# Hm this test doesn't really tickle the bug

echo $'#! /usr/bin/env \x00 sh \necho hi' > tmp.oil
env OILS_HIJACK_SHEBANG=1 $SH tmp.oil

## STDOUT:
hi
## END

#### Tea keywords don't interfere with YSH expressions

var d = {data: 'foo'}

echo $[d.data]

var e = {enum: 1, class: 2, import: 3, const: 4, var: 5, set: 6}
echo $[len(e)]

## STDOUT:
foo
6
## END

#### Catch AttributeError

var s = 'foo'
echo s=$s
var t = s.bad()
echo 'should not get here'

## status: 3
## STDOUT:
s=foo
## END


#### Command sub paren parsing bug (#1387)

write $(if (true) { write true })

const a = $(write $[len('foo')])
echo $a

const b = $(write $[5 ** 3])
echo $b

const c = $(
  write $[6 + 7]
)
echo $c

## STDOUT:
true
3
125
13
## END


#### More Command sub paren parsing

write $( var mylist = ['for']; for x in (mylist) { echo $x } )

write $( echo while; while (false) { write hi } )

write $( if (true) { write 'if' } )

write $( if (false) { write 'if' } elif (true) { write 'elif' } )

## STDOUT:
for
while
if
elif
## END

#### don't execute empty command

shopt --set ysh:all

set -x

try {
  type -a ''
}
echo "type -a returned $_status"

$(true)
echo nope

## status: 127
## STDOUT:
type -a returned 1
## END


#### Do && || with YSH constructs make sense/

# I guess there's nothing wrong with this?
#
# But I generally feel && || are only for
#
# test --file x && test --file y

var x = []
true && call x->append(42)
false && call x->append(43)
pp test_ (x)

func amp() {
  true && return (42)
}

func pipe() {
  false || return (42)
}

pp test_ (amp())
pp test_ (pipe())

## STDOUT:
## END


#### shvar then replace - bug #1986 context manager crash

shvar FOO=bar {
  for x in (1 .. 500) {
    var Q = "hello"
    setvar Q = Q=>replace("hello","world")
  }
}
echo $Q

## STDOUT:
world
## END


#### Parsing crash - bug #2003

set +o errexit

$SH -c 'proc y (;x) { return = x }'
echo status=$?

$SH -c 'func y (;x) { return = x }'
echo status=$?

## STDOUT:
status=2
status=2
## END


#### proc with IFS= read -r line - dynamic scope - issue #2012

# this is an issue with lack of dynamic scope
# not sure exactly how to handle it ...

# shvar IFS= { read } is our replacement for dynamic scope

proc p {
	read -r line
  write $line
}

proc p-ifs {
	IFS= read -r line
  write $line
}

#set -x

echo zz | p

echo yy | p-ifs

## STDOUT:
zz
yy
## END

#### func call inside proc call - error message attribution

try 2> foo {
  $SH -c '
func ident(x) {
  return (x)
}

proc p (; x) {
  echo $x
}

# BUG: it points to ( in ident(
#      should point to ( in eval (

eval (ident([1,2,3]))
'
}

cat foo

## STDOUT:
## END

