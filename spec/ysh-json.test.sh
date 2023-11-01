## oils_failures_allowed: 1
## tags: dev-minimal

#### usage errors

json read zz
echo status=$?

json write

## status: 3
## STDOUT:
status=2
## END

#### json write STRING
shopt --set parse_proc

json write ('foo')
var s = 'foo'
json write (s)
## STDOUT:
"foo"
"foo"
## END

#### json write ARRAY
json write (:|foo.cc foo.h|)
json write --indent 0 (['foo.cc', 'foo.h'])
## STDOUT:
[
  "foo.cc",
  "foo.h"
]
[
"foo.cc",
"foo.h"
]
## END

#### json write Dict
json write ({k: 'v', k2: [4, 5]})

json write ([{k: 'v', k2: 'v2'}, {}])

## STDOUT:
{
  "k": "v",
  "k2": [
    4,
    5
  ]
}
[
  {
    "k": "v",
    "k2": "v2"
  },
  {

  }
]
## END

#### json write compact format
shopt --set parse_proc

# TODO: ORDER of keys should be PRESERVED
var mydict = {name: "bob", age: 30}

json write --pretty=0 (mydict)
# ignored
json write --pretty=F --indent 4 (mydict)
## STDOUT:
{"name":"bob","age":30}
{"name":"bob","age":30}
## END

#### json write in command sub
shopt -s oil:all  # for echo
var mydict = {name: "bob", age: 30}
json write (mydict)
var x = $(json write (mydict))
echo $x
## STDOUT:
{
  "name": "bob",
  "age": 30
}
{
  "name": "bob",
  "age": 30
}
## END

#### json read passed invalid args

# EOF
json read
echo status=$?

json read 'z z'
echo status=$?

json read a b c
echo status=$?

## STDOUT:
status=1
status=2
status=2
## END

#### json read uses $_reply var

echo '{"age": 42}' | json read
json write (_reply)

## STDOUT:
{
  "age": 42
}
## END

#### json read with redirect
echo '{"age": 42}'  > $TMP/foo.txt
json read (&x) < $TMP/foo.txt
pp cell :x
## STDOUT:
x = (Cell exported:F readonly:F nameref:F val:(value.Dict d:[Dict age (value.Int i:42)]))
## END

#### json read at end of pipeline (relies on lastpipe)
echo '{"age": 43}' | json read (&y)
pp cell y
## STDOUT:
y = (Cell exported:F readonly:F nameref:F val:(value.Dict d:[Dict age (value.Int i:43)]))
## END

#### invalid JSON
echo '{' | json read (&y)
echo pipeline status = $?
pp cell y
## status: 1
## STDOUT:
pipeline status = 1
## END

#### json write expression
json write --pretty=0 ([1,2,3])
echo status=$?

json write (5, 6)  # to many args
echo status=$?

## status: 3
## STDOUT:
[1,2,3]
status=0
## END

#### json write evaluation error

#var block = ^(echo hi)
#json write (block) 
#echo status=$?

# undefined var
json write (a) 
echo status=$?

## status: 1
## STDOUT:
## END

#### json write of data structure with cycle
var L = [1, 2, 3]
setvar L[0] = L

# TODO: I guess it should exit with status 1 or 3
json write (L)

var d = {k: 'v'}
setvar d.k1 = 'v2'

# This makes it hang?  But not interactively
#setvar d.k2 = d

= d
#json write (d)

## STDOUT:
## END

#### j8 write

# TODO: much better tests
j8 write ([3, "foo"])

## STDOUT:
[
  3,
  "foo"
]
## END

