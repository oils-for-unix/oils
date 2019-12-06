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

#### json write compact format

# TODO: ORDER of keys should be PRESERVED

var mydict = {name: "bob", age: 30}

json write -pretty=0 :mydict
# ignored
json write -pretty=F -indent 4 :mydict
## STDOUT:
{"age":30,"name":"bob"}
{"age":30,"name":"bob"}
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

#### json read passed bad args
json read
echo status=$?
json read 'z z'
echo status=$?
## STDOUT:
status=2
status=2
## END


#### json read with redirect
echo '{"age": 42}'  > $TMP/foo.txt
json read :x < $TMP/foo.txt
repr :x
## STDOUT:
x = (cell val:(value.Obj obj:{'age': 42}) exported:F readonly:F)
## END

#### json read at end of pipeline (relies on lastpipe)
echo '{"age": 43}' | json read :y
repr y
## STDOUT:
y = (cell val:(value.Obj obj:{'age': 43}) exported:F readonly:F)
## END

#### invalid JSON
echo '{' | json read :y
echo pipeline status = $?
repr y
## status: 1
## STDOUT:
pipeline status = 1
## END

