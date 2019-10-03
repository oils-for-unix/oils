# Test Oil expressions within $[]

#### $[f(x)]
func f() {
  return 42
}
echo $[f()]
## STDOUT:
42
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
func f() { return 42 }
var obj = /d+/
set obj.x = 42
var d = {}
set d['key'] = 42
echo "func $[f()]"
echo "attr $[obj.x]"
echo "key $[d['key']]"
echo "key $[d->key]"
echo "dq $[d["key"]]"
## STDOUT:
func 42
attr 42
key 42
key 42
dq 42
## END
