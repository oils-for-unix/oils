## oils_failures_allowed: 2
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
  {}
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

# space before true
echo ' true' | json read
json write (_reply)

## STDOUT:
true
## END

#### json read then json write

# BUG with space before true
echo '{"name": "bob", "age": 42, "ok": true}' | json read
json write (_reply)

echo '{"name": "bob", "age": 42, "ok":true}' | json read
json write (_reply)

echo '{"name": {}, "age": {}}' | json read
json write (_reply)

## STDOUT:
{
  "name": "bob",
  "age": 42,
  "ok": true
}
{
  "name": "bob",
  "age": 42,
  "ok": true
}
{
  "name": {},
  "age": {}
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
pp line (y)
## status: 1
## STDOUT:
pipeline status = 1
## END

#### Extra data after valid JSON

# Trailing space is OK
echo '42  ' | json read
echo num space $?

echo '{}  ' | json read
echo obj space $?

echo '42 # comment' | json8 read
echo num comment $?

echo '{}   # comment ' | json8 read
echo obj comment $?

echo '42]' | json read
echo num bracket $?

echo '{}]' | json read
echo obj bracket $?

## STDOUT:
num space 0
obj space 0
num comment 0
obj comment 0
num bracket 1
obj bracket 1
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
echo 'should have failed'

## status: 1
## STDOUT:
## END

#### json write of List in cycle

var L = [1, 2, 3]
setvar L[0] = L

shopt -s ysh:upgrade
fopen >tmp.txt {
  pp line (L)
}
fgrep -n -o '[ -->' tmp.txt

json write (L)
echo 'should have failed'

## status: 1
## STDOUT:
1:[ -->
## END

#### json write of Dict in cycle

var d = {}
setvar d.k = d

shopt -s ysh:upgrade
fopen >tmp.txt {
  pp line (d)
}
fgrep -n -o '{ -->' tmp.txt

json write (d)
echo 'should have failed'

## status: 1
## STDOUT:
1:{ -->
## END

#### json write of List/Dict referenced twice (bug fix)

var mylist = [1,2,3]
var mydict = {foo: "bar"}

var top = {k: mylist, k2: mylist, k3: mydict, k4: mydict}

# BUG!
json write --pretty=F (top)

## STDOUT:
{"k":[1,2,3],"k2":[1,2,3],"k3":{"foo":"bar"},"k4":{"foo":"bar"}}
## END

#### json read doesn't accept u'' or b'' strings

json read <<EOF
{"key": u'val'}
EOF
echo status=$?

#pp line (_reply)

json read <<EOF
{"key": b'val'}
EOF
echo status=$?

## STDOUT:
status=1
status=1
## END

#### json read doesn't accept comments, but json8 does

json8 read <<EOF
{  # comment
  "key":  # zz
  b'val',  # yy
  "k2": "v2"  #
}
EOF
echo status=$?

json8 write (_reply)

json read <<EOF
{"key": "val"}  # comment
EOF
echo status=$?
## STDOUT:
status=0
{
  "key": "val",
  "k2": "v2"
}
status=1
## END


#### json write emits Unicode replacement char for binary data \yff

json write ([3, "foo", $'-\xff\xfe---\xfd=']) > tmp.txt

# Round trip it for good measure
json read < tmp.txt

json write (_reply)

## STDOUT:
[
  3,
  "foo",
  "-��---�="
]
## END

#### json8 write emits b'' strings for binary data \yff

json8 write ([3, "foo", $'-\xff\xfe-\xfd='])

## STDOUT:
[
  3,
  "foo",
  b'-\yff\yfe-\yfd='
]
## END


#### json8 write bytes vs unicode string

u=$'mu \u03bc \x01 \" \\ \b\f\n\r\t'
u2=$'\x01\x1f'  # this is a valid unicode string

b=$'\xff'  # this isn't valid unicode

json8 write (u)
json8 write (u2)

json8 write (b)

## STDOUT:
"mu μ \u0001 \" \\ \b\f\n\r\t"
"\u0001\u001f"
b'\yff'
## END

#### JSON \/ escapes supported

msg='"\/"'

echo "$msg" | python3 -c 'import json, sys; print(json.load(sys.stdin))'

echo "$msg" | json read
echo reply=$_reply

j8="b'\\/'"
echo "$msg" | json read
echo reply=$_reply


## STDOUT:
/
reply=/
reply=/
## END

#### JSON string can have unescaped ' and J8 string can have unescaped "

json read <<EOF
"'"
EOF

pp line (_reply)

json8 read <<EOF
u'"'
EOF

pp line (_reply)

## STDOUT:
(Str)   "'"
(Str)   "\""
## END


#### J8 supports superfluous \" escapes, but JSON doesn't support \' escapes

json8 read <<'EOF'
b'\"'
EOF
echo reply=$_reply

json8 read <<'EOF'
b'\'\'\b\f\n\r\t\"\\'
EOF
pp line (_reply)

# Suppress traceback
python3 -c 'import json, sys; print(json.load(sys.stdin))' 2>/dev/null <<'EOF'
"\'"
EOF
echo python3=$?

json read <<'EOF'
"\'"
EOF
echo json=$?

## STDOUT:
reply="
(Str)   "''\b\f\n\r\t\"\\"
python3=1
json=1
## END

#### Escaping uses \u0001 in "", but \u{1} in b''

s1=$'\x01'
s2=$'\x01\xff\x1f'  # byte string

json8 write (s1)
json8 write (s2)

## STDOUT:
"\u0001"
b'\u{1}\yff\u{1f}'
## END


#### json8 read

echo '{ }' | json8 read
pp line (_reply)

echo '[ ]' | json8 read
pp line (_reply)

echo '[42]' | json8 read
pp line (_reply)

echo '[true, false]' | json8 read
pp line (_reply)

echo '{"k": "v"}' | json8 read
pp line (_reply)

echo '{"k": null}' | json8 read
pp line (_reply)

echo '{"k": 1, "k2": 2}' | json8 read
pp line (_reply)

echo "{u'k': {b'k2': null}}" | json8 read
pp line (_reply)

echo '{"k": {"k2": "v2"}, "k3": "backslash \\ \" \n line 2 \u03bc "}' | json8 read
pp line (_reply)

json8 read (&x) <<'EOF'
{u'k': {u'k2': u'v2'}, u'k3': u'backslash \\ \" \n line 2 \u{3bc} '}
EOF
pp line (x)

## STDOUT:
(Dict)   {}
(List)   []
(List)   [42]
(List)   [true,false]
(Dict)   {"k":"v"}
(Dict)   {"k":null}
(Dict)   {"k":1,"k2":2}
(Dict)   {"k":{"k2":null}}
(Dict)   {"k":{"k2":"v2"},"k3":"backslash \\ \" \n line 2 μ "}
(Dict)   {"k":{"k2":"v2"},"k3":"backslash \\ \" \n line 2 μ "}
## END

#### json8 round trip

var obj = [42, 1.5, null, true, "hi", b'\yff\yfe\b\n""']

json8 write --pretty=F (obj) > j

cat j

json8 read < j

json8 write (_reply)

## STDOUT:
[42,1.5,null,true,"hi",b'\yff\yfe\b\n""']
[
  42,
  1.5,
  null,
  true,
  "hi",
  b'\yff\yfe\b\n""'
]
## END

#### json round trip (regression)

var d = {
  short: '-v', long: '--verbose', type: null, default: '', help: 'Enable verbose logging'
}

json write (d) | json read

pp line (_reply)

## STDOUT:
(Dict)   {"short":"-v","long":"--verbose","type":null,"default":"","help":"Enable verbose logging"}
## END

#### round trip: decode surrogate pair and encode

var j = r'"\ud83e\udd26"'
echo $j | json read (&c1)

json write (c1)

var j = r'"\uD83E\uDD26"'
echo $j | json read (&c2)

json write (c2)

# Not a surrogate pair
var j = r'"\u0001\u0002"' 
echo $j | json read (&c3)

json write (c3)

var j = r'"\u0100\u0101\u0102"' 
echo $j | json read (&c4)

json write (c4)

## STDOUT:
"🤦"
"🤦"
"\u0001\u0002"
"ĀāĂ"
## END

#### round trip: decode surrogate half and encode

# TODO: Weird Python allows this to be decoded, but I think the Bjoern state
# machine will not!

shopt -s ysh:upgrade

for j in '"\ud83e"' '"\udd26"' {
  var s = fromJson(j)
  pp line (s)

  # TODO: modify DFA to return the code point in the surrogate range, and
  # print it in JSON mode
  # j8 mode could possibly use byte strings
  json write (s)
}

## STDOUT:
(Str)   b'\ya0\ybe'
"\ud83e"
(Str)   b'\yb4\ya6'
"\udd26"
## END

#### toJson() toJson8() - TODO: test difference

var obj = [42, 1.5, null, true, "hi"]

echo $[toJson(obj)]
echo $[toJson8(obj)]

## STDOUT:
[42,1.5,null,true,"hi"]
[42,1.5,null,true,"hi"]
## END

#### fromJson() fromJson8() - TODO: test difference

var message ='[42,1.5,null,true,"hi"]'

pp line (fromJson(message))
pp line (fromJson8(message))

## STDOUT:
(List)   [42,1.5,null,true,"hi"]
(List)   [42,1.5,null,true,"hi"]
## END

#### User can handle errors - toJson() toJson8()
shopt -s ysh:upgrade

var obj = []
call obj->append(obj)

try {
  echo $[toJson(obj)]
}
echo status=$_status
echo "encode error $[_error.message]" | sed 's/0x[a-f0-9]\+/(object id)/'

try {  # use different style
  echo $[toJson8( /d+/ )]
}
echo status=$_status
echo "encode error $[_error.message]"

# This makes the interpreter fail with a message
echo $[toJson(obj)]

## status: 4
## STDOUT:
status=4
encode error Can't encode List (object id) in object cycle
status=4
encode error Can't serialize object of type Eggex
## END

#### User can handle errors - fromJson() fromJson8()
shopt -s ysh:upgrade

var message ='[42,1.5,null,true,"hi"'

try {
  var obj = fromJson(message)
}
echo status=$_status
echo "decode error $[_error.message]" | egrep -o '.*Expected.*RBracket'

try {
  var obj = fromJson8(message)
}
echo status=$_status
echo "decode error $[_error.message]" | egrep -o '.*Expected.*RBracket'

try {
  var obj = fromJson('[+]')
}
echo "positions $[_error.start_pos] - $[_error.end_pos]"

# This makes the interpreter fail with a message
var obj = fromJson(message)

## status: 4
## STDOUT:
status=4
decode error Expected Id.J8_RBracket
status=4
decode error Expected Id.J8_RBracket
positions 1 - 2
## END


#### ASCII control chars can't appear literally in messages
shopt -s ysh:upgrade

var message=$'"\x01"'
#echo $message | od -c

try {
  var obj = fromJson(message)
}
echo status=$_status
echo "$[_error.message]" | egrep -o 'ASCII control chars'

## STDOUT:
status=4
ASCII control chars
## END


#### \yff can't appear in u'' code strings (command)

shopt -s ysh:upgrade

echo -n b'\yfd' | od -A n -t x1
echo -n u'\yfd' | od -A n -t x1

## status: 2
## STDOUT:
 fd
## END

#### \yff can't appear in u'' code strings (expr)

var x = b'\yfe' 
write -n -- $x | od -A n -t x1

var x = u'\yfe' 
write -n -- $x | od -A n -t x1

## status: 2
## STDOUT:
 fe
## END

#### \yff can't appear in u'' multiline code strings

shopt -s ysh:upgrade

echo -n b'''\yfc''' | od -A n -t x1
echo -n u'''\yfd''' | od -A n -t x1

## status: 2
## STDOUT:
 fc
## END

#### \yff can't appear in u'' data strings

#shopt -s ysh:upgrade

json8 read (&b) <<'EOF'
b'\yfe'
EOF
pp line (b)

json8 read (&u) <<'EOF'
u'\yfe'
EOF
pp line (u)  # undefined

## status: 1
## STDOUT:
(Str)   b'\yfe'
## END

#### \u{dc00} can't be in surrogate range in code (command)

shopt -s ysh:upgrade

echo -n u'\u{dc00}' | od -A n -t x1

## status: 2
## STDOUT:
## END

#### \u{dc00} can't be in surrogate range in code (expr)

shopt -s ysh:upgrade

var x = u'\u{dc00}' 
echo $x | od -A n -t x1

## status: 2
## STDOUT:
## END

#### \u{dc00} can't be in surrogate range in data

json8 read <<'EOF'
["long string", u'hello \u{d7ff}', "other"]
EOF
echo status=$?

json8 read <<'EOF'
["long string", u'hello \u{d800}', "other"]
EOF
echo status=$?

json8 read <<'EOF'
["long string", u'hello \u{dfff}', "other"]
EOF
echo status=$?

json8 read <<'EOF'
["long string", u'hello \u{e000}', "other"]
EOF
echo status=$?


## STDOUT:
status=0
status=1
status=1
status=0
## END



#### Inf and NaN can't be encoded or decoded

# This works in Python, should probably support it

var n = float("NaN")
var i = float("inf")

pp line (n)
pp line (i)

json dump (n)
json dump (i)

## status: 2
## STDOUT:
## END

#### Invalid UTF-8 in JSON is rejected

echo $'"\xff"' | json read
echo status=$?

echo $'"\xff"' | json8 read
echo status=$?

echo $'\xff' | json read
echo status=$?

echo $'\xff' | json8 read
echo status=$?

## STDOUT:
status=1
status=1
status=1
status=1
## END

#### Invalid JSON in J8 is rejected

json8 read <<EOF
b'$(echo -e -n '\xff')'
EOF
echo status=$?

json8 read <<EOF
u'$(echo -e -n '\xff')'
EOF
echo status=$?

## STDOUT:
status=1
status=1
## END

#### '' means the same thing as u''

echo "''" | json8 read
pp line (_reply)

echo "'\u{3bc}'" | json8 read
pp line (_reply)

echo "'\yff'" | json8 read
echo status=$?

## STDOUT:
(Str)   ""
(Str)   "μ"
status=1
## END

#### decode deeply nested structure (stack overflow)

shopt -s ysh:upgrade

proc pairs(n) {
  var m = int(n)  # TODO: 1 .. n should auto-convert?

  for i in (1 .. m) {
    write -n -- '['
  }
  for i in (1 .. m) {
    write -n -- ']'
  }
}

# This is all Python can handle; C++ can handle more
msg=$(pairs 50)

#echo $msg

echo "$msg" | json read
pp line (_reply)
echo len=$[len(_reply)]

## STDOUT:
(List)   [[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]
len=1
## END

#### decode integer larger than 2^32

json=$(( 1 << 33 ))
echo $json

echo $json | json read
pp line (_reply)

## STDOUT:
8589934592
(Int)   8589934592
## END

#### round trip: read/write with ysh

var file = "$REPO_ROOT/spec/testdata/bug.json"
#cat $file
cat $file | json read (&cfg)
json write (cfg) > ysh-json

diff -u $file ysh-json
echo diff=$?

## STDOUT:
diff=0
## END

#### round trip: read/write with ysh, read/write with Python 3 (bug regression)

var file = "$REPO_ROOT/spec/testdata/bug.json"
#cat $file
cat $file | json read (&cfg)
json write (cfg) > ysh-json

cat ysh-json | python3 -c \
  'import json, sys; obj = json.load(sys.stdin); json.dump(obj, sys.stdout, indent=2); print()' \
  > py-json

diff -u $file py-json
echo diff=$?

## STDOUT:
diff=0
## END

#### Encoding bytes that don't hit UTF8_REJECT immediately (bug fix)

var x = $'\xce'
json8 write (x)
declare -p x
echo

var y = $'\xbc'
json8 write (y)
declare -p y
echo

var z = $'\xf0\x9f\xa4\xff'
json8 write (z)
declare -p z

## STDOUT:
b'\yce'
declare -- x=$'\xce'

b'\ybc'
declare -- y=$'\xbc'

b'\yf0\y9f\ya4\yff'
declare -- z=$'\xf0\x9f\xa4\xff'
## END

#### NIL8 token in JSON / JSON8

echo "(" | json read
echo status=$?

echo ")" | json8 read
echo status=$?

## STDOUT:
status=1
status=1
## END
