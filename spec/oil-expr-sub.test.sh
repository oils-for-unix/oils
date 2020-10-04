# Test Oil expressions within $[]

#### $[f(x)]
var a = %(a b c)
echo $[len(a)]
## STDOUT:
3
## END

#### $[obj.attr]
var obj = /d+/
set obj.x = 42
echo $[obj.x]
## STDOUT:
42
## END

#### $[d['key']]
var d = {}
set d['key'] = 42
echo $[d['key']]
## STDOUT:
42
## END

#### $[d->key]
var d = {}
set d['key'] = 42
echo $[d->key]
## STDOUT:
42
## END

#### In Double quotes
var a = %(a b c)
var obj = /d+/
set obj.x = 42
var d = {}
set d['key'] = 42
echo "func $[len(a)]"
echo "attr $[obj.x]"
echo "key $[d['key']]"
echo "key $[d->key]"
echo "dq $[d["key"]]"
## STDOUT:
func 3
attr 42
key 42
key 42
dq 42
## END
