# Test out Oil's JSON support.

#### json write STRING
myvar='foo'
json write myvar
json write :myvar
## STDOUT:
"foo"
"foo"
## END

#### json write ARRAY
a=(foo.cc foo.h)
json write :a
json write -indent 0 :a
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

#### json write in command sub
shopt -s oil:all  # for echo
var mydict = {name: "bob", age: 30}
json write :mydict
var x = $(json write :mydict)
echo $x
## STDOUT:
{
  "age": 30,
  "name": "bob"
}
{
  "age": 30,
  "name": "bob"
}
## END

