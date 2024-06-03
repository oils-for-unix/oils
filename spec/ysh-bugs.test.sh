## our_shell: ysh
## oils_failures_allowed: 1

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


#### && || with YSH constructs ?


var x = []
true && call x->append(42)
false && call x->append(43)
pp line (x)


func amp() {
  true && return (42)
}

func pipe() {
  false || return (42)
}

pp line (amp())
pp line (pipe())

## STDOUT:
## END


